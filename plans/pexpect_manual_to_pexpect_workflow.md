# Workflow: Capture Manual Terminal Sessions and Generate pexpect Automation

This document describes a repeatable workflow for:

- Capturing manual command-line sessions robustly (interactive or scripted) using `script -f <logfile>`.
- Post-processing and sanitizing the logs for analysis.
- Submitting logs to Copilot for automated analysis and generation of a pexpect script that reproduces the manual sequence.
- Integrating the generated pexpect script into the repository's existing pexpect tooling and testing it.

Repository references (useful integration points):

- [`lib/pexpect_dev/session_logger.py`](lib/pexpect_dev/session_logger.py:1)
- [`bin/modules/step_engine_library_curDev/pexpect_test/pexpect_handler.py`](bin/modules/step_engine_library_curDev/pexpect_test/pexpect_handler.py:1)
- Other examples and logs: [`bin/docs/tutorials/pexpect_test/logs/interactions/session_session_25c59d01_summary.txt`](bin/docs/tutorials/pexpect_test/logs/interactions/session_session_25c59d01_summary.txt:1)

1) Prerequisites and safety

- Ensure you have `script`, `sed`, `col`, `tmux` (optional) installed.
- Sanitize sensitive data before submitting logs to any external service: redact IPs, hostnames, usernames, UUIDs, API keys, tokens, SSH keys, and passwords. Use deterministic redaction so Copilot can still see structure (e.g., REPLACED_USER_1, REPLACED_HOST_1).
- Do not paste private keys, full tokens, or passwords. If a password interaction occurred, replace the actual password with `<PASSWORD_REDACTED>` and leave the prompt/echo visible.
- Keep a local copy of raw logs and a redacted copy to submit. Store raw logs in a secure location (e.g., encrypted directory).

2) Exact CLI commands and options to start/stop `script`

Interactive shell capture (foreground)

```bash
# Start recording a typescript with timestamps via env var for later processing
script -q -f -c "$SHELL" ./session-$(date +%Y%m%d_%H%M%S).typescript
# Do manual work in the shell; Ctrl-D or exit stops recording
```

Capture a single command or non-interactive sequence (one-shot)

```bash
# Run a command and capture its output
script -q -f ./session-$(date +%Y%m%d_%H%M%S).typescript -- sh -c 'your-command arg1 arg2'
```

Run `script` in background (detached) using nohup or tmux

```bash
# With nohup (simple background)
nohup script -q -f ./session.x.typescript &
# Save PID to manage
echo $! > session_script.pid

# Prefer tmux for robust interactive sessions
tmux new-session -d -s session_record "script -q -f /path/to/session.typescript"
# Attach later via: tmux attach -t session_record
# Stop: send 'exit' to the shell inside tmux or kill the tmux session
```

Start/stop notes

- Use `script -q -f` to force flushing (-f) and quiet header (-q).
- Use a timestamped filename and include a session id marker in the file name.
- If you need to capture a multi-window tmux session, run script in each pane.

3) Recommended log formatting and post-processing

Desired log features

- Each user-entered command line should be delimited with a session marker and timestamp.
- Preserve prompts, command echo, and important outputs.
- Normalized timestamps provide ordering context.

Embedding session markers (practice)

- Before starting manual work, run an explicit sentinel to mark session start:

```bash
echo "==SESSION_START: $(date -u +%FT%TZ) ID=session-$(date +%s) USER=$USER HOST=$(hostname)" >&2
```

- And at the end:

```bash
echo "==SESSION_END: $(date -u +%FT%TZ) ID=session-$(date +%s)" >&2
```

Post-processing steps (normalize control characters, color codes, and prompts)

- Remove ANSI escapes and control sequences

```bash
# remove control characters including color sequences
cat raw.typescript | sed -u 's/\x1b\[[0-9;]*[A-Za-z]//g' | col -b > cleaned_step1.txt
```

- Collapse backspaces and carriage-returns

```bash
# Remove backspaces/backtracking
perl -pe '1 while s/.\x08//g' cleaned_step1.txt > cleaned_step2.txt
# Or use col -b (may help): cat raw | col -b > cleaned.txt
```

- Insert timestamps for lines without timestamps (optional)

```bash
# Prefix each non-empty line with the capture timestamp (approximate)
awk 'BEGIN{ORS=""} /==SESSION_/{print $0 "\n"; next} { print strftime("[%Y-%m-%dT%H:%M:%SZ] ") $0 "\n" }' cleaned_step2.txt > cleaned_timestamped.txt
```

- Identify and extract the command lines (heuristic)

Use a regex to find likely commands: lines starting with typical prompts (e.g., user@host:~$, >, #) or lines that were echoed right after a prompt marker. Example extraction with grep/sed:

```bash
# crude: lines that look like prompts followed by commands
grep -E "^[^\n]*\$ |^# |^> " cleaned_step2.txt -n
```

4) Step-by-step: handing the log to Copilot

- Provide Copilot the cleaned, redacted log only (not raw). Keep the log length reasonable: prefer extracts that cover the sequence needed (e.g., 200-1000 lines). If large, provide an excerpt that covers the start-to-end of the task.
- Prefix your submission with a short context: what goal to automate, environment (local/ssh/telnet), any passwords replaced by <PASSWORD_REDACTED>, and which lines were redacted.

Example paste structure you give Copilot:

```
CONTEXT: Automate the following manual session that configures X on host Y via SSH. Passwords replaced with <PASSWORD_REDACTED>. Environment: local pexpect-based test harness.

--- START LOG ---
[cleaned_timestamped.txt contents; trimmed to relevant range]
--- END LOG ---

INSTRUCTION: Extract the sequence of commands, expected prompts, and outputs. Produce a Python pexpect script that reproduces the sequence with spawn/send/expect, timeout and retry behavior, and placeholders for secrets.

DO NOT return raw secrets; annotate any redacted sections with tokens.
```

What to avoid

- Do not paste raw private keys, tokens, or full passwords.
- Avoid extremely long untrimmed logs. If you must submit long logs, attach them via an allowed file upload mechanism and provide a focused excerpt in the prompt.

5) Analysis approach Copilot should follow

Provide Copilot with instructions to follow this deterministic analysis path:

- Step A — Identify session boundaries: locate SESSION_START / SESSION_END markers or infer from timestamps.
- Step B — Normalize prompts: cluster recurring prompt patterns (e.g., "user@host:~$ ", "root@host# ", "> "). Treat any prompt that changes (e.g., becomes "config-mode>") as a state transition.
- Step C — Extract commands: find lines that appear to be user input (immediately following a prompt). Record the exact string and surrounding expected output lines (until next prompt or blank line).
- Step D — Classify interaction type: simple command (run and return), password prompt (expect password-like prompt), interactive menu (expect numbered choices), long-running command (expect no prompt for > N seconds), or streaming output.
- Step E — Produce steps: for each extracted command produce a step with fields {expect_prompt, send, expect_output_regex, timeout, retry_policy}.
- Step F — Insert redaction placeholders for any sensitive matches and include comments where human validation is required.

6) pexpect script template (pseudocode + sample Python snippet)

Pseudocode mapping

- For each step:
  - spawn(target)
  - expect(expect_prompt, timeout)
  - sendline(command)
  - expect(output_regex or prompt, timeout)
  - if expect timed out: optionally retry N times with backoff
  - handle password prompts by sending redacted placeholder

Python example (include language declaration)

```python
import pexpect
import re

class SessionRunner:
    def __init__(self, cmd, logfile_path=None, default_timeout=10):
        self.child = pexpect.spawn(cmd, encoding='utf-8', timeout=default_timeout)
        if logfile_path:
            self.child.logfile = open(logfile_path, 'w')

    def run_step(self, expect_prompt, send_cmd=None, expect_regex=None, timeout=10, retries=1):
        for attempt in range(1, retries+1):
            try:
                self.child.expect(expect_prompt, timeout=timeout)
                if send_cmd is not None:
                    self.child.sendline(send_cmd)
                if expect_regex:
                    self.child.expect(expect_regex, timeout=timeout)
                return True
            except pexpect.TIMEOUT:
                if attempt == retries:
                    raise
                else:
                    continue

# Example generated sequence
if __name__ == '__main__':
    runner = SessionRunner('ssh user@host', logfile_path='auto_session.log')
    # expect password prompt and send placeholder
    runner.run_step(expect_prompt=r'password:', send_cmd='<PASSWORD_REDACTED>', expect_regex=r'[$#>]')
    # run a prepared command and expect prompt
    runner.run_step(expect_prompt=r'[$#>]', send_cmd='sudo systemctl status myservice', expect_regex=r'Active:')
```

Handling timeouts, retries, and password prompts

- Use pexpect.TIMEOUT exceptions to implement retries with exponential backoff.
- For password prompts, never embed plaintext secrets in code — instead read from an environment variable, a local secrets file with restricted permissions, or prompt the user at runtime.

7) Edge cases and error handling

- Partial commands or line-editing: logs might have backspaces; post-processing must normalize these (see post-processing step). If uncertain, add a human-review step.
- Interactive menus: map to sendline(number) with expect of menu redisplay or newline; detect by seeing repeated menu lines.
- Dynamic prompts: use regex patterns for prompts (e.g., r"^[\w@-]+[\[\]?:~/\w-]*[#$>] \s*$").
- Long-running commands: detect by lack of prompt for > X seconds; use expect with a long timeout or expect for a completion marker.
- Flaky commands: include retry_policy: {attempts:3, backoff: [1,2,4]}.
- Commands that change terminal state (e.g., vim, less): these are not easily automatable by sendline; add a note for manual rewriting or specialized handling.

8) Integration notes with this repository

- Use the existing session logger and handler as integration points:
  - Inspect [`lib/pexpect_dev/session_logger.py`](lib/pexpect_dev/session_logger.py:1) to mirror logging conventions and re-use helper functions for timestamps and redaction.
  - Place generated scripts under `bin/modules/step_engine_library_curDev/pexpect_test/generated/` and register them with the `spawn_manager` or test harness used by other pexpect examples.
  - Review [`bin/modules/step_engine_library_curDev/pexpect_test/pexpect_handler.py`](bin/modules/step_engine_library_curDev/pexpect_test/pexpect_handler.py:1) for patterns around spawn lifecycle and logging.

Suggested integration steps

1. Save generated script as `generated/<session_id>_auto.py`.
2. Add a small wrapper that configures logging and reads secret placeholders from env (e.g., $AUTOMATION_PASSWORD).
3. Add tests under `bin/modules/step_engine_library_curDev/pexpect_test/tests_generated.py` that run in a controlled environment (mocked service or local echo server).
4. Add CI job to run lint and a dry-run of generated scripts in a sandbox environment.

9) Testing steps (dry run, logging, CI integration)

Local dry run

- Run the generated script with verbose logging redirected to a file and a console copy:

```bash
python generated/session123_auto.py 2>&1 | tee generated/session123_auto.runlog
```

- Inspect logs and compare the runlog to the original cleaned typescript to confirm expected outputs.

Automated tests

- Create unit tests that mock pexpect.spawn (use monkeypatch) to simulate expected prompts and outputs, validate that the script sends correct commands and handles retries/timeouts.

CI integration

- Add a job that lints generated scripts and runs their unit tests in a sandboxed environment. Do not run scripts that access production systems.

Appendix: Quick redaction helper

```bash
# redact emails, IPs, and tokens in-place producing redacted.txt
sed -E -e 's/[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+/REDACTED_IP/g' \
    -e 's/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/REDACTED_EMAIL/g' \
    -e 's/([A-Za-z0-9_\-]{20,})/REDACTED_TOKEN/g' cleaned_timestamped.txt > redacted.txt
```

Contact and validation

- After Copilot produces a candidate pexpect script, run it against a staging environment and verify each step. Maintain an audit trail of raw logs, redacted logs, and generated scripts.



