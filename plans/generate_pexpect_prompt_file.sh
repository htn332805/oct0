#!/bin/bash
# Script to generate reusable Pexpect development prompt
set -e

TARGET="framework-spec/pexpect-prompt.md"
DIR=$(dirname "$TARGET")

if [ ! -f "$DIR/.write_exception" ] && [ ! -f ".write_exception" ]; then
    echo "⚠️ Cannot write $TARGET — .write_exception missing"
    exit 1
fi

mkdir -p "$DIR"

cat > "$TARGET" <<'EOF'
# Reusable Pexpect Development Prompt

## Global Rules
- No file/directory can be modified unless a `.write_exception` exists
- memory-bank/ is read-only; never modify
- Only pexpect-memory/ and logs/ are writable

## Logging
- Logs in logs/ with ISO 8601 timestamps
- [INPUT], [OUTPUT], [ERROR], [PROMPT], [TIMEOUT]

## Shell Environment
- Visible interactive bash shells
- tmux optional for dev only; production scripts must be tmux-free
- User can send commands manually; AI may also send commands

## Pexpect Dev Guidelines
- Spawn shells via pexpect.spawn("/bin/bash")
- Capture all input/output with logging
- Handle prompts, timeouts, errors
- Scripts standalone; no tmux

## AI-Assisted Development
- Suggest script skeletons from previous sessions
- Propose expect patterns using pexpect-memory
- Highlight timing or prompt issues
- Include logging code if missing

## Session Management
- SESSION_ID: PEXPECT_SESSION_<timestamp>
- RESUME_POINTS optional
- Shell persists until user sends GOODBYE

## Reuse Instructions
- Copy this file for each new Pexpect script
- Reference pexpect-memory for consistency
- Maintain modular, maintainable, observable scripts
EOF

echo "✅ $TARGET generated successfully."