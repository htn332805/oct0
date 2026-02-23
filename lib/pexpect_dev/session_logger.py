#!/usr/bin/env python3
"""
Transparent Session Logger

Spawns an interactive shell and logs all I/O in the background.
User interacts normally while everything is recorded for later analysis.

Usage:
    python -m lib.pexpect_dev.session_logger [--shell /bin/bash] [--log-dir ./.sessions] [--name my_session]

    # To stop: type "GOODBYE" or exit the shell normally.
"""

import sys
import pty
import os
import select
import termios
import tty
import fcntl
import argparse
import threading
import queue
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict
import json

# Regex to strip ANSI escape sequences from terminal output. [web:2][web:3]
ANSI_ESCAPE_RE = re.compile(r"(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]")
# Matches semicolon-prefixed fragments terminated by BEL (e.g. ;HasRichCommandDetection=...\x07)
BEL_FRAGMENT_RE = re.compile(r';[^\x07]*\x07')
# Bracketed OSC/device-status sequences with OR without ESC prefix (catches \x1b]... and bare ]...)
# Matches: \x1b]...\x07 OR \x1b]...ESC\ patterns (standard OSC with proper terminators only)
# Note: DOES NOT match bare ]633;X patterns - those are shell markers handled separately
OSC_BRACKETED_RE = re.compile(r'(?:\x1b\][^\x07\x1b\]]*(?:\x07|\x1b\\))')
# Corrupted/bare title sequences from shells (xterm OSC title codes)
# Matches: [0;..., ]0;..., []0;... and similar title set sequences
# Pattern: ([ or ]) (optional [ or ]) digit ; content ]
BRACKET_TITLE_RE = re.compile(r'(?:\[|\])[\[\]]?[0-9];[^\]]*\]')
# Bare ]633 sequences (incomplete/corrupted markers without ESC prefix)
# Handles both:
# 1. Repeated bare markers: ]633]633]633...
# 2. Bare parameterized: ]633;P;Cwd=/path;A;...
# Character class allows semicolons (part of param structure), stops at ] or whitespace
BRACKET_SEQ_AGGRESSIVE_RE = re.compile(r']633(?:;[^\[\]\s]*)*')
# Cleanup for orphaned numeric fragments left after sequence removal (e.g., "633;A" or "633;B")
# These are remnants of malformed/concatenated sequences
# Now matches any token that STARTS with the pattern (e.g., "633;Adf", "633;A(pyenv)")
ORPHAN_DIGIT_FRAG_RE = re.compile(r'^[0-9]+;[A-Z]')
# C0 control chars excluding newline, carriage return and tab (more aggressive: includes BEL, backspace)
CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')

class TransparentSessionLogger:
    """
    Transparent shell session logger with background monitoring.

    - User interacts with a real shell.
    - All I/O is captured, timestamped, line-buffered, and cleaned of ANSI codes.
    """

    def __init__(
        self,
        shell: str = "/bin/bash",
        log_dir: str = "./.sessions",
        session_name: Optional[str] = None,
    ):
        self.shell = shell
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = session_name or f"session_{timestamp}"

        # Log files
        self.log_file = self.log_dir / f"{self.session_id}.log"
        self.metadata_file = self.log_dir / f"{self.session_id}.json"

        # PTY handles
        self.master_fd: Optional[int] = None
        self.slave_fd: Optional[int] = None
        self.child_pid: Optional[int] = None

        # Terminal state
        self.old_tty = None
        self.running = False

        # Optional queues if you want to hook this into other agents later
        self.input_queue = queue.Queue()
        self.output_queue = queue.Queue()

        # Line buffers for INPUT and OUTPUT
        self.input_buffer: bytes = b""
        self.output_buffer: bytes = b""

        # Track sent input to detect echoes in output
        # When user types something, it gets echoed back by the shell through PTY
        # We need to detect this and classify it as INPUT, not OUTPUT
        self.last_sent_input: bytes = b""

        # Statistics
        self.stats = {
            "bytes_sent": 0,
            "bytes_received": 0,
            "lines_input": 0,
            "lines_output": 0,
            "commands_entered": [],
            "start_time": datetime.now().isoformat(),
            "end_time": None,
        }
        self._last_logged_line: dict[str, tuple[datetime, str]] = {}

    # ---------- PTY and terminal management ----------

    def _create_pty(self) -> None:
        """Create pseudo-terminal pair and set master non-blocking."""
        self.master_fd, self.slave_fd = pty.openpty()

        # Set non-blocking mode on master
        flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
        fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

    def _spawn_shell(self) -> None:
        """Fork and spawn shell in slave PTY."""
        self.child_pid = os.fork()

        if self.child_pid == 0:
            # Child process
            os.close(self.master_fd)

            # Make slave FD the controlling terminal
            os.setsid()
            os.dup2(self.slave_fd, 0)  # stdin
            os.dup2(self.slave_fd, 1)  # stdout
            os.dup2(self.slave_fd, 2)  # stderr

            if self.slave_fd > 2:
                os.close(self.slave_fd)

            env = os.environ.copy()
            env["TERM"] = "xterm-256color"

            os.execvpe(self.shell, [self.shell], env)
            sys.exit(1)

        # Parent process
        os.close(self.slave_fd)

    def _set_terminal_raw(self) -> None:
        """Set terminal to raw mode for passthrough."""
        self.old_tty = termios.tcgetattr(sys.stdin)
        tty.setraw(sys.stdin.fileno())

    def _restore_terminal(self) -> None:
        """Restore terminal settings."""
        if self.old_tty:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_tty)

    # ---------- Logging helpers ----------

    def _is_echoed_input(self, text: str) -> bool:
        """
        Detect if a line is an echo of user input (shell prompt + command).
        
        Shell prompts typically end with $, #, or > and are followed by a command.
        Examples:
        - (pyenv) tester@LC1UNVME:~/Projects/octo/bin/instances/tmp$ df -hT
        - nixos@nixos:~]$ exit
        - root@host:/home# ls -la
        - user@host> echo hello
        
        Pattern: [prompt-like-content]($ or # or >) [command]
        """
        # Detect prompt patterns: ends with $ or # or > followed by space and non-whitespace
        # This catches lines like "prompt$ command", "prompt# command", "prompt> command"
        if re.search(r'[#$>]\s+\S+', text):
            return True
        return False

    def _sanitize_for_log(self, data: bytes | str) -> str:
        """
        Decode bytes, normalize newlines, strip ANSI escape codes,
        and remove trailing newline (logger adds its own).
        Aggressively removes OSC, bracket sequences, and control characters.
        """
        if isinstance(data, bytes):
            text = data.decode("utf-8", errors="replace")
        else:
            text = data

        # Normalize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Strip CSI/SS3 style ANSI escape sequences [web:2][web:3]
        text = ANSI_ESCAPE_RE.sub("", text)

        # IMPORTANT: Remove proper OSC sequences BEFORE general BEL fragments
        # (OSC_BRACKETED_RE must match complete sequences before BEL_FRAGMENT_RE strips contents)
        text = OSC_BRACKETED_RE.sub("", text)

        # Remove semicolon-prefixed BEL fragments (some terminals embed short ;key=val\x07 fragments)
        # This now only catches leftover fragments, not complete OSC sequences
        text = BEL_FRAGMENT_RE.sub("", text)

        # Remove corrupted/bare title sequences like [0;... or [1;...
        text = BRACKET_TITLE_RE.sub("", text)

        # Remove aggressive bare bracket sequences like ]633;A or ]633;P;Cwd=...
        # Apply in a loop because sequences can be repeated (e.g., ]633]633]633)
        prev = None
        while prev != text:
            prev = text
            text = BRACKET_SEQ_AGGRESSIVE_RE.sub("", text)

        # Remove remaining C0 control characters (including BEL and DEL)
        text = CTRL_RE.sub("", text)

        # Clean up orphaned numeric sequence fragments (e.g., "633;A" or "633;B" left after removal)
        # Split by spaces to handle each token, remove fragments, rejoin
        tokens = text.split()
        cleaned_tokens = [t for t in tokens if not ORPHAN_DIGIT_FRAG_RE.match(t)]
        text = ' '.join(cleaned_tokens)

        # Remove stray bracket characters and bracket patterns that are escape code remnants
        # (bare [ at start, [] patterns, [0; patterns from corrupted title sequences)
        text = re.sub(r'^\[', '', text)  # Remove leading [
        text = re.sub(r'\[\]', '', text)  # Remove [] pattern
        text = re.sub(r'\[[0-9];', '', text)  # Remove [0; style title patterns still present

        # Remove trailing newline characters; we'll add a single '\n' when writing
        text = text.rstrip("\n")
        
        # Final check: if line is empty or only whitespace, return empty
        # (this is important to filter out lines that were ONLY escape codes)
        # But keep any line with actual content, including prompts like "$ " or "# "
        if not text.strip():
            return ""

        return text


    def _write_log_line(self, entry_type: str, text: str) -> None:
        """
        Write a single sanitized log line in the format:

        [YYYY-MM-DD HH:MM:SS.mmm] [TYPE] [SESSION_ID] text

        Deduplicates exact repeats or near-repeats within 1.0 second windows.
        """
        now = datetime.now()
        # Deduplicate: skip lines that match (exactly or as substring of) the last line
        # within a 1.0 second window to catch PTY echoes and rapid duplicates
        last = self._last_logged_line.get(entry_type)
        if last:
            last_time, last_text = last
            elapsed = (now - last_time).total_seconds()
            # Skip if exact match within 1.0s, or if this text is short and appeared within 0.1s
            # (catches rapid PTY echoes/rebounderments)
            if elapsed < 1.0:
                if (last_text == text) or (elapsed < 0.1 and len(text) < 200 and text in last_text):
                    return
        self._last_logged_line[entry_type] = (now, text)
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{entry_type}] [{self.session_id}] {text}\n"
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(line)

    def log_marker(self, text: str) -> None:
        """Public helper to add a MARKER entry into the log."""
        self._write_log_line("MARKER", text)

    def _log_chunk(self, entry_type: str, chunk: bytes, is_input: bool) -> None:
        """
        Append chunk to the appropriate buffer, split into complete lines,
        and log each complete line as a separate entry.
        
        Also detects echoed input (shell prompt + command in OUTPUT) and reclassifies it.
        """
        # Update byte stats with raw data
        if is_input:
            self.stats["bytes_sent"] += len(chunk)
            # Track what was sent for echo detection
            self.last_sent_input = chunk
        else:
            self.stats["bytes_received"] += len(chunk)

        buf_attr = "input_buffer" if is_input else "output_buffer"
        buf = getattr(self, buf_attr) + chunk

        while True:
            nl_pos = buf.find(b"\n")
            if nl_pos == -1:
                break

            line_bytes = buf[: nl_pos + 1]
            buf = buf[nl_pos + 1 :]

            text = self._sanitize_for_log(line_bytes)
            if text:
                # Classify: if OUTPUT looks like echoed input (prompt + command), reclassify as INPUT
                actual_entry_type = entry_type
                if entry_type == "OUTPUT" and self._is_echoed_input(text):
                    actual_entry_type = "INPUT"
                
                self._write_log_line(actual_entry_type, text)
                
                # Update stats with actual entry type
                if actual_entry_type == "INPUT":
                    self.stats["lines_input"] += 1
                else:
                    self.stats["lines_output"] += 1

        setattr(self, buf_attr, buf)

    def _flush_partial_lines(self) -> None:
        """Flush any remaining partial lines when the session ends."""
        for entry_type, buf_attr, is_input in [
            ("INPUT", "input_buffer", True),
            ("OUTPUT", "output_buffer", False),
        ]:
            buf = getattr(self, buf_attr)
            if buf:
                text = self._sanitize_for_log(buf)
                if text:
                    # Reclassify echoed input in OUTPUT as INPUT
                    actual_entry_type = entry_type
                    if entry_type == "OUTPUT" and self._is_echoed_input(text):
                        actual_entry_type = "INPUT"
                    
                    self._write_log_line(actual_entry_type, text)
            setattr(self, buf_attr, b"")

    # ---------- I/O threads ----------

    def _check_goodbye(self, data: bytes) -> bool:
        """Check if user typed GOODBYE to end session."""
        try:
            text = data.decode("utf-8", errors="replace").strip().upper()
            return text == "GOODBYE"
        except Exception:
            return False

    def _input_thread(self) -> None:
        """Thread to handle user input (stdin -> PTY + log)."""
        while self.running:
            try:
                data = os.read(sys.stdin.fileno(), 4096)
                if not data:
                    break

                if self._check_goodbye(data):
                    self._write_log_line("INFO", "GOODBYE received - ending session")
                    self.running = False
                    break

                # Forward to child PTY
                if self.master_fd is not None:
                    os.write(self.master_fd, data)

                # Line-buffered logging
                self._log_chunk("INPUT", data, is_input=True)

            except OSError:
                break
            except Exception as e:
                self._write_log_line("ERROR", f"Input thread error: {e}")

    def _output_thread(self) -> None:
        """Thread to handle shell output (PTY -> stdout + log)."""
        while self.running:
            try:
                if self.master_fd is None:
                    break

                ready, _, _ = select.select([self.master_fd], [], [], 0.1)
                if not ready:
                    continue

                data = os.read(self.master_fd, 4096)
                if not data:
                    # Shell exited
                    self._write_log_line("INFO", "Shell exited")
                    self.running = False
                    break

                # Echo to user
                os.write(sys.stdout.fileno(), data)

                # Line-buffered logging
                self._log_chunk("OUTPUT", data, is_input=False)

            except OSError:
                break
            except select.error:
                continue
            except Exception as e:
                self._write_log_line("ERROR", f"Output thread error: {e}")

    # ---------- Summary and lifecycle ----------

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate session summary and write metadata JSON."""
        self.stats["end_time"] = datetime.now().isoformat()
        self.stats["duration_seconds"] = (
            datetime.fromisoformat(self.stats["end_time"])
            - datetime.fromisoformat(self.stats["start_time"])
        ).total_seconds()

        summary = {
            "session_id": self.session_id,
            "shell": self.shell,
            "statistics": self.stats,
            "log_file": str(self.log_file),
            "start_time": self.stats["start_time"],
            "end_time": self.stats["end_time"],
        }

        with self.metadata_file.open("w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary

    def run(self) -> None:
        """Run the transparent logging session."""
        print("")
        print("🚀 Starting transparent session logger")
        print(f"   Session ID: {self.session_id}")
        print(f"   Shell:      {self.shell}")
        print(f"   Log:        {self.log_file}")
        print("")
        print("   Type 'GOODBYE' or exit the shell to end session")
        print("   Press Enter to start...")
        print("")

        input()  # Wait for user to be ready

        try:
            self._create_pty()
            self._spawn_shell()
            self._set_terminal_raw()

            self.running = True

            self._write_log_line("INFO", f"Session started: {self.session_id}")
            self._write_log_line("INFO", f"Shell: {self.shell}")

            input_thread = threading.Thread(target=self._input_thread, daemon=True)
            output_thread = threading.Thread(target=self._output_thread, daemon=True)

            input_thread.start()
            output_thread.start()

            input_thread.join()
            output_thread.join()

        except KeyboardInterrupt:
            self._write_log_line("INFO", "Session interrupted by user (Ctrl+C)")
        except Exception as e:
            self._write_log_line("ERROR", f"Session error: {e}")
        finally:
            self.running = False
            self._restore_terminal()

            if self.master_fd is not None:
                try:
                    os.close(self.master_fd)
                except OSError:
                    pass

            if self.child_pid:
                try:
                    os.kill(self.child_pid, 9)
                except ProcessLookupError:
                    pass

            # Flush any partial lines not terminated by newline
            self._flush_partial_lines()

            summary = self._generate_summary()

            print("\n\n📊 Session Summary:")
            print(f"   Duration: {summary['statistics']['duration_seconds']:.2f}s")
            print(f"   Input:    {summary['statistics']['bytes_sent']} bytes")
            print(f"   Output:   {summary['statistics']['bytes_received']} bytes")
            print(f"   Log:      {self.log_file}")

def main() -> None:
    parser = argparse.ArgumentParser(description="Transparent Shell Session Logger")
    parser.add_argument(
        "--shell",
        default="/bin/bash",
        help="Shell to spawn (default: /bin/bash)",
    )
    parser.add_argument(
        "--log-dir",
        default="./.sessions",
        help="Directory for log files",
    )
    parser.add_argument(
        "--name",
        help="Session name (auto-generated if not provided)",
    )

    args = parser.parse_args()

    logger = TransparentSessionLogger(
        shell=args.shell,
        log_dir=args.log_dir,
        session_name=args.name,
    )
    logger.run()


if __name__ == "__main__":
    main()

