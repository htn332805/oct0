ssh_session_pexpect.py — interrupt / control-character notes
=========================================

This file documents the `--interrupt` CLI flag available in `ssh_session_pexpect.py` (located in the same `generated/` directory).

Purpose
-------
When a spawned remote process has left the terminal in a state where prompts are not matching (long-running processes, pager, or other interactive state), the script can attempt a configurable sequence of control characters before retrying the expect. Use `--interrupt` to provide one or more control characters or control sequences the script should send before sending an Enter and retrying.

Supported token forms
---------------------
- Caret notation: `^C` — sends Ctrl+C (SIGINT equivalent). Any `^X` where X is a single character is supported.
- Hyphen notation: `C-c`, `ctrl-c`, `c-c` — will be parsed and treated as Ctrl+C (last character used).
- Hex escape: `\x03`, `\x1b` — send the literal byte(s) specified by the hex code.
- Single character: `q` — sends the literal character `q`.
- Arbitrary literal: any other string is sent literally (best-effort).

Examples
--------
1) Basic local-test: send Ctrl+C on retry (useful to interrupt a running command like `top`):

```bash
python generated/ssh_session_pexpect.py --local-test --prompt-retries 3 --interrupt '^C'
```

2) Use hex-style interrupt (same as ^C):

```bash
python generated/ssh_session_pexpect.py --host 1.2.3.4 --user me --prompt-retries 2 --interrupt '\x03'
```

3) Provide multiple interrupts (will be sent in order each retry):

```bash
python generated/ssh_session_pexpect.py --host 1.2.3.4 --user me \
  --prompt-retries 3 --interrupt '^C' --interrupt '\x1b' --interrupt 'q'
```

4) SSH example where you want to send Ctrl+C then Enter before retrying the prompt:

```bash
python generated/ssh_session_pexpect.py --host host.example --user alice \
  --prompt-retries 2 --interrupt 'C-c'
```

Behavior notes
--------------
- On an expect TIMEOUT or EOF (or when a sentinel like `pexpect.TIMEOUT`/`pexpect.EOF` was provided in a patterns list and matched), the script will perform the configured interrupts (in the order provided), then send an Enter (`\n`), and retry the expect up to `--prompt-retries` times.
- Interrupts are best-effort: some terminals or remote processes may ignore control characters, or the environment may map them differently.
- For most interrupt needs, `^C` (Ctrl-C) or `\x03` are the simplest and most portable options.

Security and safety
-------------------
- Sending control characters may affect the remote process (for example, Ctrl+C can terminate a running job). Use with caution on production systems.
- The script performs interrupts automatically when prompts fail to match; if you prefer manual control, set `--prompt-retries 0`.

Where to edit
-------------
- The implementation is in `generated/ssh_session_pexpect.py` (search for `_build_interrupt_actions`, `_do_interrupts`, and `expect_with_retries`).

Feedback
--------
If you need additional sequences (for example, escape + '[' + 'A' for arrow-up sequences) or to send timing-separated sequences, tell me and I can add a simple syntax for grouped sequences or delays between sends.
