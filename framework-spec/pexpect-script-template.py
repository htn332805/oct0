#!/usr/bin/env python3
"""
Pexpect Script Template
- Reusable for interactive CLI automation
- Logs inputs/outputs to logs/ with timestamp and [INPUT]/[OUTPUT] markers
- Standalone, no tmux dependency
"""

import pexpect
import datetime
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

def timestamp():
    return datetime.datetime.now().isoformat()

def log(shell_name, type_, message):
    filename = f"{LOG_DIR}/{shell_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    with open(filename, "a") as f:
        f.write(f"[{type_}][{timestamp()}] {message}\n")

def main():
    shell = pexpect.spawn("/bin/bash", encoding='utf-8', echo=False)
    shell.sendline("echo Hello World")
    log("shell1", "INPUT", "echo Hello World")
    shell.expect("\n")
    output = shell.before.strip()
    log("shell1", "OUTPUT", output)
    shell.interact()

if __name__ == "__main__":
    main()
