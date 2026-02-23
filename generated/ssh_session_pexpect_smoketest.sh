#!/usr/bin/env bash
# Smoke test for generated/ssh_session_pexpect.py demonstrating --interrupt behavior
# This runs the script in --local-test mode and forces a short expect timeout so
# the script will send the configured interrupt (Ctrl+C) and retry.

PY=python
SCRIPT="generated/ssh_session_pexpect.py"

# Run with a short timeout so `sleep 5` will cause an expect TIMEOUT and trigger the interrupt
$PY $SCRIPT --local-test --timeout 1 --prompt-retries 1 --interrupt '^C' --commands "sleep 5" "echo after"
