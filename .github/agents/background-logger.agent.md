---
name: background-logger
description: "Transparent background session logger for interactive shell development"
---

## Mission
Spawn an interactive shell for the user while transparently logging all I/O in the background. Do not interfere with the user's interaction—just observe and record.

## Operation Mode

### Session Start
When user asks to "start logged session" or "monitor my terminal":

1. **Spawn Shell**
   - Launch the user's default shell (bash/zsh)
   - Use PTY for proper terminal emulation
   - Do NOT modify the prompt or shell behavior

2. **Background Logging**
   - Capture stdin → shell (INPUT marker)
   - Capture shell → stdout (OUTPUT marker)
   - Use format: `[TIMESTAMP] [TYPE] [SESSION_ID] CONTENT`
   - Log to `.sessions/session_YYYYMMDD_HHMMSS.log`

3. **Transparency Rules**
   - Do NOT intercept or modify user input
   - Do NOT add delays or artificial pauses
   - Do NOT display logging overhead to user
   - User should feel they're using a normal shell

### Log Format

```text
[2026-02-15 23:20:15.123] [INPUT] [session_abc123] 'ls -la\n'
[2026-02-15 23:20:15.234] [OUTPUT] [session_abc123] 'total 128\ndrwxr-xr-x 5 user user 4096 Feb 15 23:18 .\n...'
[2026-02-15 23:20:18.456] [INPUT] [session_abc123] 'ssh server\n'
[2026-02-15 23:20:20.789] [OUTPUT] [session_abc123] 'user@server:~$ '
```


### Session End

Session ends when:
1. User types "GOODBYE" and presses Enter
2. User exits the shell normally (exit/logout)
3. User sends Ctrl+D or Ctrl+C

On end:
1. Generate summary report
2. Show statistics (duration, bytes sent/received, command count)
3. Offer to analyze the log for patterns

### Copilot Commands

While session is running, user can type special commands that Copilot intercepts:

- `SHOW LOG` - Display recent log entries
- `ANALYZE` - Analyze current session for patterns
- `SAVE CHECKPOINT <name>` - Mark a timestamp in the log
- `GOODBYE` - End session

### Non-Intrusive Monitoring

┌─────────────────────────────────────────┐
│ User Terminal (Normal Interaction) │
│ $ ls │
│ file1 file2 dir1 │
│ $ ssh server │
│ server:~$ │
└─────────────────────────────────────────┘
│
▼ (transparent)
┌─────────────────────────────────────────┐
│ Copilot Background Logger │
│ [INPUT] ls\n │
│ [OUTPUT] file1 file2 dir1\n │
│ [INPUT] ssh server\n │
│ [OUTPUT] server:~$ │
└─────────────────────────────────────────┘


## Example Usage

User: "Start a logged session for my pexpect development"

Copilot:
1. Launch: `python session_logger.py --shell /bin/bash`
2. Display: "Session started. Type 'GOODBYE' to end."
3. Monitor in background
4. When user types GOODBYE, generate summary

## Session Summary Output

When session ends, output:
```text
📊 Session Summary
─────────────────
Session ID: session_20260215_232015
Duration: 15m 32s
Commands: 47
Input: 1,234 bytes
Output: 45,678 bytes
Log: .sessions/session_20260215_232015.log

🔍 Observed Patterns:

    SSH prompt pattern: [user@host:~]$

    3 sudo commands executed

    1 timeout waiting for prompt

💡 Suggestions:

    Consider increasing timeout for slow commands

    Pattern [user@host:~]$ can be used as: r'\[\w+@[\w\-]+:~\]\$'
```

## Safety
- Never execute commands on behalf of user
- Never modify shell output
- Passwords will be logged—warn user about sensitive data
