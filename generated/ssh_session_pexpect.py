#!/usr/bin/env python3
"""
ssh_session_pexpect.py

Replicates the session in the log:
 - ssh to user@host
 - supply password (from env or prompt)
 - set a deterministic prompt
 - run: df -hT
 - run: uptime
 - exit and save a session log

Usage:
    python ssh_session_pexpect.py --host 172.28.94.183 --user nixos
    OR
    SSH_PASSWORD=secret python ssh_session_pexpect.py --host 172.28.94.183 --user nixos

Tip: run `python ssh_session_pexpect.py --help` to display full CLI options and examples.

Commands:
    By default the script runs: df -hT and uptime. You can override commands with either:
        --commands "cmd1" "cmd2"  (provide commands on CLI)
    OR
        --cmd-file cmd.txt           (one command per line; supports # comments)
    Example cmd.txt:
        # update and show disk
        df -hT
        uptime

Notes:
 - Avoid hardcoding real passwords; use SSH keys when possible.
 - The script disables strict host key checking for automation; remove those options for production.
 
Interrupt flag (--interrupt)
--------------------------------
 - Use `--interrupt` to supply control characters or sequences the script will send when an expect fails to match (TIMEOUT/EOF). This helps interrupt long-running remote processes (for example, send Ctrl+C to stop a pager) before the script retries the expect.
 - Supported tokens include caret notation (`^C`), hyphen notation (`C-c`/`ctrl-c`), hex escapes (`\x03`), or literal characters. Use `--interrupt` multiple times to send a sequence.
 - Behavior: on retry the script sends configured interrupts (in order), then sends an Enter, and retries the expect up to `--prompt-retries` times.
"""

import argparse
import datetime
import getpass
import os
import pexpect
import re
import sys

def main():
    p = argparse.ArgumentParser(
        description="Automate SSH/telnet sessions and stream output; supports prompt-retry and --interrupt to send control characters when prompts hang."
    )
    p.add_argument("--host", required=False, help="Target host/IP (not required with --local-test)")
    p.add_argument("--user", required=False, help="SSH username (not required with --local-test)")
    p.add_argument("--port", type=int, default=22, help="Port (SSH default 22; for telnet set custom port)")
    p.add_argument("--proto", choices=["ssh", "telnet"], default="ssh",
                   help="Protocol to use: ssh (default) or telnet")
    p.add_argument("--commands", nargs="*", default=["df -hT", "uptime"], help="Commands to run on remote")
    p.add_argument("--logdir", default=".sessions", help="Directory to write session log")
    p.add_argument("--timeout", type=int, default=60, help="Expect timeout (s)")
    p.add_argument("--send-delay", type=float, default=0.02,
                   help="Delay (seconds) inserted before each send to the child (reduces timing races).")
    p.add_argument("--preserve-ansi", action="store_true",
                   help="When set, preserve ANSI sequences in the saved logfile (by default ANSI is stripped).")
    p.add_argument("--strip-bracketed", action="store_true",
                   help="When set, additionally strip bracketed OSC sequences (\x1b]... ) from the logfile. Use with caution: may remove legitimate output.")
    p.add_argument("--prompt-retries", type=int, default=2,
                   help="Number of times to retry a matched EOF/TIMEOUT by sending Enter (and optional interrupts) before failing")
    p.add_argument("--interrupt", action="append", default=[],
                   help=("Control character(s) to send before retrying when a prompt isn't matched. "
                         "Examples: '^C', 'C-c', '\\x03', '\\x1b'. Can be used multiple times."))
    p.add_argument("--cmd-file", dest="cmd_file", default=None,
                   help="Path to a text file containing commands (one per line). Lines starting with # and blank lines are ignored.")
    p.add_argument("--disable-host-key-check", action="store_true",
                   help="Disable SSH host key checking (adds StrictHostKeyChecking=no and UserKnownHostsFile=/dev/null)")
    p.add_argument("--identity-file", "-i", dest="identity_file", default=None,
                   help="Path to private key identity file to use for SSH authentication")
    p.add_argument("--local-test", action="store_true",
                   help="Run a local interactive /bin/bash to test streaming, prompts and errors")
    p.add_argument("--simulate-auth-fail", action="store_true",
                   help="When used with --local-test, simulate an authentication failure path and exit with code 3")
    args = p.parse_args()

    # Basic argument validation
    if not (1 <= args.port <= 65535):
        print(f"ERROR: --port must be between 1 and 65535 (got {args.port})", file=sys.stderr)
        sys.exit(2)
    if args.identity_file:
        if args.proto != "ssh":
            print("WARNING: --identity-file is only applicable to ssh; ignoring for telnet", file=sys.stderr)
        if not os.path.isfile(args.identity_file):
            print(f"ERROR: identity file not found: {args.identity_file}", file=sys.stderr)
            sys.exit(2)
    if args.cmd_file:
        if not os.path.isfile(args.cmd_file):
            print(f"ERROR: command file not found: {args.cmd_file}", file=sys.stderr)
            sys.exit(2)
        # Read commands from file, ignore blank lines and comments
        with open(args.cmd_file, "r", encoding="utf-8") as cf:
            lines = [ln.rstrip('\n') for ln in cf]
        file_cmds = [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith('#')]
        if not file_cmds:
            print(f"ERROR: command file {args.cmd_file} contains no commands", file=sys.stderr)
            sys.exit(2)
        args.commands = file_cmds

    password = os.environ.get("SSH_PASSWORD")
    # Only prompt for a password if not running local-test and no identity file is provided and no SSH_PASSWORD env var
    if not args.local_test and not password and not args.identity_file:
        try:
            password = getpass.getpass(f"Password for {args.user}@{args.host}: ")
        except Exception:
            password = None

    os.makedirs(args.logdir, exist_ok=True)
    timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    logfile_path = os.path.join(args.logdir, f"session_{timestamp}.log")

    # If local test mode, spawn an interactive bash instead of ssh
    if args.local_test:
        child = pexpect.spawn('/bin/bash', ['-i'], encoding="utf-8", timeout=args.timeout)
    else:
        # require host and user when not in local-test
        if not args.host or not args.user:
            print("ERROR: --host and --user are required unless --local-test is used", file=sys.stderr)
            sys.exit(2)
        # Build command based on protocol
        if args.proto == "ssh":
            ssh_parts = ["ssh"]
            if args.disable_host_key_check:
                ssh_parts += ["-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null"]
            if args.identity_file:
                ssh_parts += ["-i", args.identity_file]
            ssh_parts += ["-p", str(args.port), f"{args.user}@{args.host}"]
            ssh_cmd = " ".join(sh for sh in ssh_parts)
            child = pexpect.spawn(ssh_cmd, encoding="utf-8", timeout=args.timeout)
        elif args.proto == "telnet":
            # telnet <host> <port>
            telnet_cmd = f"telnet {args.host} {args.port}"
            child = pexpect.spawn(telnet_cmd, encoding="utf-8", timeout=args.timeout)
        else:
            print(f"ERROR: Unsupported protocol: {args.proto}", file=sys.stderr)
            sys.exit(2)
    # save full interaction and stream live output to stdout

    with open(logfile_path, "w", encoding="utf-8") as logf:
        # CleanFileWriter writes raw output to stdout but strips ANSI sequences before
        # writing to the persistent logfile. We attach it to child.logfile_read so only
        # bytes read from the child are saved (avoids duplicate sent-lines in the log).
        class CleanFileWriter:
            # Generic ANSI escape sequences (CSI/SS3/OSC etc)
            _ansi_re = re.compile(r'(?:\x1B[@-_][0-?]*[ -/]*[@-~])')
            # semicolon-prefixed fragments terminated by BEL (e.g. ;HasRichCommandDetection=...\x07)
            _bel_fragment_re = re.compile(r';[^\x07]*\x07')
            # C0 control chars excluding newline, carriage return and tab
            _ctrl_re = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')
            # Bracketed OSC/Device-status sequences starting with ESC ] and optionally terminated
            # by BEL or ESC \; we bound the length to avoid runaway removal in case of no terminator.
            _osc_bracketed_re = re.compile(r'\x1b\][^\x07\x1b]{0,200}(?:\x07|\x1b\\)?')

            def __init__(self, fileobj, stdout_obj, preserve=False, strip_bracketed=False):
                self.file = fileobj
                self.stdout = stdout_obj
                self.preserve = preserve
                self.strip_bracketed = bool(strip_bracketed)

            def _clean(self, s):
                # strip ANSI CSI/OSC sequences
                s = self._ansi_re.sub('', s)
                # remove semicolon-prefixed fragments terminated by BEL (e.g. ;HasRichCommandDetection=...\x07)
                s = self._bel_fragment_re.sub('', s)
                # optionally remove bracketed OSC/device-status sequences (may risk removing legit output)
                if self.strip_bracketed:
                    s = self._osc_bracketed_re.sub('', s)
                # remove remaining C0 control chars except newline, carriage return, and tab
                s = self._ctrl_re.sub('', s)
                return s

            def write(self, s):
                if s is None:
                    return 0
                # write raw to stdout so interactive colors remain
                try:
                    self.stdout.write(s)
                except Exception:
                    pass
                # write to logfile: either preserve ANSI or strip/clean it
                try:
                    if self.preserve:
                        self.file.write(s)
                    else:
                        clean = self._clean(s)
                        self.file.write(clean)
                except Exception:
                    pass
                try:
                    return len(s)
                except Exception:
                    return 0

            def flush(self):
                try:
                    self.stdout.flush()
                except Exception:
                    pass
                try:
                    self.file.flush()
                except Exception:
                    pass

        clean_writer = CleanFileWriter(logf, sys.stdout, preserve=bool(args.preserve_ansi), strip_bracketed=bool(args.strip_bracketed))
        # attach to logfile_read to avoid logging what we send
        child.logfile_read = clean_writer
        # configure send delay per CLI
        try:
            child.delaybeforesend = float(args.send_delay)
        except Exception:
            pass

        # Helper: parse interrupt argument strings into callable actions that send to child
        def _build_interrupt_actions(interrupt_list):
            actions = []
            for token in interrupt_list:
                t = token.strip()
                if not t:
                    continue
                # ^X style
                if len(t) == 2 and t[0] == '^':
                    ch = t[1]
                    actions.append(("control", ch))
                    continue
                # ctrl-x, C-x, c-x, C-x, c-x style
                if ('ctrl-' in t.lower()) or ('c-' in t.lower()) or ('c' == t.lower().split('-')[0] if '-' in t else False):
                    # take last char
                    parts = t.split('-')
                    last = parts[-1]
                    if last:
                        actions.append(("control", last[0]))
                        continue
                # \xNN hex style
                if t.startswith('\\x') or t.startswith('\\X'):
                    try:
                        hexpart = t[2:]
                        val = int(hexpart, 16)
                        actions.append(("literal", chr(val)))
                        continue
                    except Exception:
                        pass
                # plain single char
                if len(t) == 1:
                    actions.append(("literal", t))
                    continue
                # fallback: send the token as-is
                actions.append(("literal", t))
            return actions

        interrupt_actions = _build_interrupt_actions(args.interrupt)

        # Helper: perform interrupts on the child
        def _do_interrupts(child):
            for typ, val in interrupt_actions:
                try:
                    if typ == "control":
                        # pexpect.sendcontrol expects a single character like 'c' for ^C
                        child.sendcontrol(val.lower())
                    else:
                        # literal string (may include escape sequences already parsed)
                        child.send(val)
                except Exception:
                    # best-effort: ignore send failures
                    pass

        # Wrapper to call child.expect with retries. If patterns include pexpect.EOF or pexpect.TIMEOUT
        # and that index is returned, treat as a failed match and retry by sending interrupts + Enter.
        def expect_with_retries(child, patterns, timeout, retries):
            # Normalize patterns to a list
            pats = patterns if isinstance(patterns, (list, tuple)) else [patterns]
            for attempt in range(retries + 1):
                try:
                    idx = child.expect(pats, timeout=timeout)
                    # If the matched pattern is the pexpect sentinel, optionally retry
                    matched = pats[idx] if idx < len(pats) else None
                    if matched in (pexpect.EOF, pexpect.TIMEOUT):
                        if attempt < retries:
                            _do_interrupts(child)
                            # send an Enter to try to wake the prompt
                            try:
                                child.sendline('')
                            except Exception:
                                pass
                            continue
                        # exhausted retries; return the index (same as original behavior)
                    return idx
                except (pexpect.TIMEOUT, pexpect.EOF) as e:
                    # When expect raises, retry if we still have attempts left
                    if attempt < retries:
                        _do_interrupts(child)
                        try:
                            child.sendline('')
                        except Exception:
                            pass
                        continue
                    # exhausted retries: re-raise to let outer handlers manage
                    raise

        # If requested, simulate an authentication failure in local-test mode
        if args.local_test and args.simulate_auth_fail:
            sim_msg = "Permission denied, please try again.\n"
            # write simulated auth failure to both logfile and stdout
            clean_writer.write(sim_msg)
            clean_writer.flush()
            child.close()
            print("ERROR: Simulated authentication failure (local-test).", file=sys.stderr)
            sys.exit(3)

        try:
            # Branch behavior depending on protocol and local-test
            if args.local_test:
                # Local interactive bash: set prompt and run commands
                child.sendline('export PS1="PEXPECT_PROMPT> "')
                expect_with_retries(child, "PEXPECT_PROMPT> ", timeout=10, retries=args.prompt_retries)
                for cmd in args.commands:
                    child.sendline(cmd)
                    expect_with_retries(child, "PEXPECT_PROMPT> ", timeout=args.timeout, retries=args.prompt_retries)
                child.sendline("exit")
                expect_with_retries(child, [pexpect.EOF], timeout=20, retries=args.prompt_retries)

            elif args.proto == "ssh":
                i = expect_with_retries(child,
                    [r"are you sure you want to continue connecting", r"[Pp]assword:", pexpect.EOF, pexpect.TIMEOUT],
                    timeout=15, retries=args.prompt_retries
                )
                if i == 0:
                    # Accept new host key prompt
                    child.sendline("yes")
                    # expect password prompt next
                    expect_with_retries(child, r"[Pp]assword:", timeout=15, retries=args.prompt_retries)
                    i = 1

                if i == 1:
                    if password is None and not args.identity_file:
                        # No password and no identity file - allow ssh to prompt/fail
                        pass
                    elif password is not None:
                        child.sendline(password)

                # After sending credentials (or none), detect auth success/failure
                auth_index = expect_with_retries(child, [
                    r"[Pp]ermission denied",    # auth failure
                    r"Connection closed by",    # connection closed
                    r"Last login:",             # successful login banner
                    r"\n.*[$#] ",               # shell prompt
                    r"PEXPECT_PROMPT> ",         # our later prompt possibly echoed
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ], timeout=15, retries=args.prompt_retries)

                if auth_index in (0, 1):
                    msg = (child.before or "").strip()
                    print(f"ERROR: Authentication failed for {args.user}@{args.host}.\n{msg}", file=sys.stderr)
                    child.close()
                    sys.exit(3)
                if auth_index in (5, 6):
                    msg = (child.before or "").strip()
                    print(f"ERROR: Connection failed during authentication to {args.user}@{args.host}.\n{msg}", file=sys.stderr)
                    child.close()
                    sys.exit(4)

                # Successful login detected; set a deterministic prompt
                child.sendline('export PS1="PEXPECT_PROMPT> "')
                expect_with_retries(child, "PEXPECT_PROMPT> ", timeout=10, retries=args.prompt_retries)

                # Run the requested commands; output will stream live via child.logfile
                for cmd in args.commands:
                    child.sendline(cmd)
                    # wait for the prompt indicating the command finished
                    expect_with_retries(child, "PEXPECT_PROMPT> ", timeout=args.timeout, retries=args.prompt_retries)

                # exit the remote shell
                child.sendline("exit")
                # wait for EOF/close
                expect_with_retries(child, [pexpect.EOF], timeout=20, retries=args.prompt_retries)

            elif args.proto == "telnet":
                # Telnet authentication flow: handle a wider range of login/username and password prompts
                init_index = expect_with_retries(child, [
                    # username/login prompts (many variants)
                    r"(?:[Ll]ogin(?: as)?:|[Uu]sername:|[Uu]ser:|[Ee]nter username:|[Pp]lease login:)",
                    # password or passphrase prompts
                    r"[Pp](?:ass(?:word|phrase))(?: for .*?)?:",
                    # common failure messages
                    r"[Ll]ogin incorrect|[Aa]ccess denied|[Ii]nvalid user|[Ii]nvalid login",
                    # connection errors
                    r"Connection (?:refused|closed) by|Connection closed",
                    # any shell-like prompt (>, #, $)
                    r"\n.*[>#\$]",
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ], timeout=15, retries=args.prompt_retries)

                if init_index == 0:
                    # username prompt
                    if not args.user:
                        print("ERROR: Telnet login requires --user", file=sys.stderr)
                        child.close()
                        sys.exit(2)
                    child.sendline(args.user)
                    # expect password or prompt
                    post_index = expect_with_retries(child, [
                        r"[Pp](?:ass(?:word|phrase))(?: for .*?)?:",
                        r"\n.*[>#\\$]",
                        r"[Ll]ogin incorrect|[Aa]ccess denied|[Ii]nvalid user|[Ii]nvalid login",
                        pexpect.EOF,
                        pexpect.TIMEOUT,
                    ], timeout=15, retries=args.prompt_retries)
                    if post_index == 0:
                        # password prompt
                        if password is not None:
                            child.sendline(password)
                    elif post_index == 2:
                        print(f"ERROR: Authentication failed for {args.user}@{args.host} (telnet).", file=sys.stderr)
                        child.close()
                        sys.exit(3)
                elif init_index == 1:
                    # password prompt immediately
                    if password is not None:
                        child.sendline(password)
                elif init_index in (2, 3):
                    # login incorrect or connection closed/refused
                    print(f"ERROR: Authentication/connection failure to {args.host} (telnet).", file=sys.stderr)
                    child.close()
                    sys.exit(3)
                elif init_index in (5, 6):
                    print(f"ERROR: Connection failed to {args.host} (telnet).", file=sys.stderr)
                    child.close()
                    sys.exit(4)

                # After credentials, check for success or failure
                post_auth = expect_with_retries(child, [
                    r"[Pp]ermission denied",
                    r"[Ll]ogin incorrect|[Aa]ccess denied|[Ii]nvalid user|[Ii]nvalid login",
                    r"\n.*[>#\\$]",
                    pexpect.EOF,
                    pexpect.TIMEOUT,
                ], timeout=15, retries=args.prompt_retries)
                if post_auth in (0, 1):
                    msg = (child.before or "").strip()
                    print(f"ERROR: Authentication failed for {args.user}@{args.host} (telnet).\n{msg}", file=sys.stderr)
                    child.close()
                    sys.exit(3)
                if post_auth in (3, 4):
                    msg = (child.before or "").strip()
                    print(f"ERROR: Connection failed during authentication to {args.host} (telnet).\n{msg}", file=sys.stderr)
                    child.close()
                    sys.exit(4)

                # Successful telnet connection: attempt to set a deterministic prompt
                try:
                    child.sendline('export PS1="PEXPECT_PROMPT> "')
                    expect_with_retries(child, "PEXPECT_PROMPT> ", timeout=10, retries=args.prompt_retries)
                except Exception:
                    # if setting prompt fails, continue and rely on existing prompt detection
                    pass

                # Run commands and wait for either our prompt or a generic shell prompt
                for cmd in args.commands:
                    child.sendline(cmd)
                    expect_with_retries(child, ["PEXPECT_PROMPT> ", r"\n.*[>#\\$]"], timeout=args.timeout, retries=args.prompt_retries)

                # exit
                child.sendline("exit")
                expect_with_retries(child, [pexpect.EOF], timeout=20, retries=args.prompt_retries)

        except pexpect.TIMEOUT:
            print("ERROR: Expect timed out.", file=sys.stderr)
            child.close()
            sys.exit(5)
        except pexpect.EOF:
            print("ERROR: Remote closed connection unexpectedly.", file=sys.stderr)
            child.close()
            sys.exit(6)

    print(f"Session log saved to: {logfile_path}")

if __name__ == "__main__":
    main()