---
name: Start Pexpect Development Session
description: Launch an interactive terminal monitoring session for pexpect script development
tool choice: auto
---

## Context
You are about to start an interactive pexpect development session. The user wants to manually explore a CLI workflow while you monitor and capture all interactions.

## Session Parameters
{{#if target_command}}
**Target Command**: {{target_command}}
{{/if}}
{{#if objective}}
**Session Objective**: {{objective}}
{{/if}}
{{#if timeout}}
**Default Timeout**: {{timeout}} seconds
{{else}}
**Default Timeout**: 30 seconds
{{/if}}

## Startup Checklist

1. **Confirm Understanding**
   - Restate the objective in your own words
   - Confirm the target command/program to automate
   - Ask about any expected prompts or authentication steps

2. **Establish Monitoring**
   - Explain the logging format: `[TIMESTAMP] [TYPE] Content`
   - Create session log file path
   - Generate SESSION_ID
   - State the session end conditions

3. **Provide Quick Commands**
   Teach the user these session control phrases:
   - `SAVE CHECKPOINT <name>` - Mark a resume point
   - `SHOW BUFFER` - Display current expect buffer contents
   - `ANALYZE LAST` - Review last interaction for issues
   - `GENERATE CODE` - Create pexpect script from session log
   - `GOODBYE` - End session and generate final report

4. **Spawn Terminal**
   - Open integrated terminal in VS Code
   - Start the target command if provided
   - Begin monitoring and logging immediately

## During Session

For each interaction:
1. Log the user's input with `[INPUT]` marker and timestamp
2. Log all terminal output with `[OUTPUT]` marker and timestamp
3. Classify detected prompts with `[PROMPT]` marker
4. Record timeout events with `[TIMEOUT]` marker
5. Offer analysis when patterns emerge or issues occur

## Log Format Example

```text
[2026-02-15 21:30:15.245] [INPUT] ssh admin@router.example.com
[2026-02-15 21:30:17.891] [OUTPUT]
[2026-02-15 21:30:17.892] [PROMPT] Password:
[2026-02-15 21:30:20.123] [INPUT] ******
[2026-02-15 21:30:20.456] [PROMPT] router>
[2026-02-15 21:30:25.789] [INPUT] show version
[2026-02-15 21:30:26.012] [OUTPUT] Cisco IOS Software...
[2026-02-15 21:30:26.100] [PROMPT] router>
[2026-02-15 21:30:30.500] [RESUME_POINT] Post-authentication, ready for configuration commands
```


## Session End

When the session ends (objective met or "GOODBYE"):
1. Generate a summary report
2. Create a skeleton pexpect script from the session log
3. Offer to save the script to a file
4. Close the log file

Begin now by confirming the session objective.

# Example User Input
```text
@pexpect-interactive Start session: automating SSH to my router and running show commands

@pexpect-interactive Start session: automating SSH to my router and running show commands

Checkpoint Example:
SAVE CHECKPOINT after-auth

Generating Code:
When you type GENERATE CODE
```
