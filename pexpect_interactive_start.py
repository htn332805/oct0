#!/usr/bin/env python3
"""
Interactive Pexpect Development Session (Dual-Shell with tmux)

Launches two interactive shells in a tmux session with comprehensive logging.

Features:
- Two interactive shells in tmux split panes (left/right)
- Bi-directional communication between shells
- All I/O logged separately with [TIMESTAMP] [INPUT|OUTPUT|ERROR] markers
- ANSI escape sequences stripped for clean analysis logs
- Manual command entry in either shell at any time
- Type 'GOODBYE' or exit shell to end session
- Automatic JSON metadata and summary statistics for both shells
- Mouse enabled for easy pane selection

Development vs. Production:
- Development: Uses tmux for visual interaction with 2 shells
- Production: Final pexpect script will use pure pexpect (no tmux)
  with two independent spawn children for bi-directional automation

Usage:
    python3 pexpect_interactive_start.py [--shell /bin/bash] [--name session_name]
"""

import sys
import argparse
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent))

from lib.pexpect_dev.session_logger import TransparentSessionLogger


class DualShellTmuxSession:
    """Manages a dual-shell development session using tmux."""

    def __init__(self, shell: str, log_dir: str, session_name: str):
        self.shell = shell
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_name = session_name
        self.tmux_session_name = f"pexpect_dev_{session_name}"
        
        self.shell_left_name = f"{session_name}_shell_left"
        self.shell_right_name = f"{session_name}_shell_right"

    def create_tmux_session(self) -> bool:
        """Create tmux session with 2 panes."""
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", self.tmux_session_name],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("ERROR: tmux not found. Install with: apt-get install tmux")
            return False

        try:
            subprocess.run(
                [
                    "tmux",
                    "new-session",
                    "-d",
                    "-s", self.tmux_session_name,
                    "-x", "220",
                    "-y", "50",
                    "-c", str(Path.cwd()),
                ],
                check=True,
            )

            subprocess.run(
                ["tmux", "set-option", "-t", self.tmux_session_name, "mouse", "on"],
                check=True,
            )

            subprocess.run(
                [
                    "tmux",
                    "split-window",
                    "-t", self.tmux_session_name,
                    "-h",
                ],
                check=True,
            )

            left_cmd = f"python3 -c 'import sys; sys.path.insert(0, \"{Path(__file__).parent}\"); from lib.pexpect_dev.session_logger import TransparentSessionLogger; logger = TransparentSessionLogger(shell=\"{self.shell}\", log_dir=\"{self.log_dir}\", session_name=\"{self.shell_left_name}\"); logger.run()'"
            
            subprocess.run(
                [
                    "tmux",
                    "send-keys",
                    "-t", f"{self.tmux_session_name}:0.0",
                    left_cmd,
                    "Enter",
                ],
                check=True,
            )

            right_cmd = f"python3 -c 'import sys; sys.path.insert(0, \"{Path(__file__).parent}\"); from lib.pexpect_dev.session_logger import TransparentSessionLogger; logger = TransparentSessionLogger(shell=\"{self.shell}\", log_dir=\"{self.log_dir}\", session_name=\"{self.shell_right_name}\"); logger.run()'"
            
            subprocess.run(
                [
                    "tmux",
                    "send-keys",
                    "-t", f"{self.tmux_session_name}:0.1",
                    right_cmd,
                    "Enter",
                ],
                check=True,
            )

            return True

        except subprocess.CalledProcessError as e:
            print(f"ERROR creating tmux session: {e}")
            return False
        except FileNotFoundError:
            print("ERROR: tmux not found")
            return False

    def attach_to_tmux(self) -> None:
        """Attach to tmux session."""
        try:
            subprocess.run(
                ["tmux", "attach-session", "-t", self.tmux_session_name],
            )
        except KeyboardInterrupt:
            pass

    def cleanup(self) -> None:
        """Clean up tmux session."""
        try:
            subprocess.run(
                ["tmux", "kill-session", "-t", self.tmux_session_name],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            pass

    def load_session_metadata(self) -> Tuple[dict, dict]:
        """Load metadata from both session logs."""
        left_meta = {}
        right_meta = {}
        
        left_meta_file = self.log_dir / f"{self.shell_left_name}.json"
        right_meta_file = self.log_dir / f"{self.shell_right_name}.json"
        
        if left_meta_file.exists():
            try:
                left_meta = json.loads(left_meta_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        
        if right_meta_file.exists():
            try:
                right_meta = json.loads(right_meta_file.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        
        return left_meta, right_meta

    def run(self) -> None:
        """Run the dual-shell development session."""
        print_banner()
        print(f"Session ID: {self.session_name}")
        print(f"Shell:      {self.shell}")
        print(f"Log Dir:    {self.log_dir.resolve()}")
        print("")
        print("Tmux Session (2 Panes):")
        print(f"  Session Name: {self.tmux_session_name}")
        print("  Left Pane:   Shell 1 (PARENT)")
        print("  Right Pane:  Shell 2 (CHILD)")
        print("")
        
        print_dual_instructions()

        if not self.create_tmux_session():
            sys.exit(1)

        print(f"Tmux session created: {self.tmux_session_name}")
        print("Attaching to session... (Press Ctrl+B then D to detach)\n")
        
        time.sleep(1)
        self.attach_to_tmux()

        print("\nWaiting for loggers to flush...\n")
        time.sleep(2)

        left_meta, right_meta = self.load_session_metadata()
        print_final_summary(
            self.session_name,
            self.shell_left_name,
            self.shell_right_name,
            left_meta,
            right_meta,
            self.log_dir,
        )

        self.cleanup()


def print_banner():
    """Print banner."""
    print("\n")
    print("=" * 80)
    print(" INTERACTIVE PEXPECT DEVELOPMENT SESSION (DUAL-SHELL)".center(80))
    print("=" * 80)
    print("")


def print_dual_instructions():
    """Print instructions."""
    print("INSTRUCTIONS:")
    print("")
    print("  Navigation:")
    print("    - Left Pane:  Ctrl+B, then Left Arrow (or click with mouse)")
    print("    - Right Pane: Ctrl+B, then Right Arrow (or click with mouse)")
    print("    - Mouse:      Enabled - click on pane to switch")
    print("")
    print("  Operations:")
    print("    - Type commands freely in either pane")
    print("    - Exchange data between shells manually for testing")
    print("    - All I/O is logged with [TIMESTAMP] [INPUT|OUTPUT] markers")
    print("    - ANSI codes are stripped for clean analysis")
    print("")
    print("  Session Control:")
    print("    - Detach:     Ctrl+B, then D")
    print("    - Exit:       Type 'GOODBYE' or 'exit' in each pane")
    print("")


def print_final_summary(
    session_name: str,
    shell_left_name: str,
    shell_right_name: str,
    left_meta: dict,
    right_meta: dict,
    log_dir: Path,
):
    """Print summary."""
    print("=" * 80)
    print(" DUAL-SHELL SESSION COMPLETE".center(80))
    print("=" * 80)
    print("")
    
    print(f"Session Summary: {session_name}")
    print("")
    
    print("-" * 80)
    print(f"SHELL 1 (LEFT PANE): {shell_left_name}")
    print("-" * 80)
    if left_meta:
        stats = left_meta.get("statistics", {})
        duration = stats.get('duration_seconds', 'N/A')
        if isinstance(duration, float):
            duration = f"{duration:.2f}s"
        print(f"  Duration:       {duration}")
        print(f"  Input:          {stats.get('bytes_sent', 0)} bytes")
        print(f"  Output:         {stats.get('bytes_received', 0)} bytes")
        print(f"  Input Lines:    {stats.get('lines_input', 0)}")
        print(f"  Output Lines:   {stats.get('lines_output', 0)}")
    else:
        print("  (No metadata found)")
    
    log_file = log_dir / f"{shell_left_name}.log"
    print(f"  Log File:       {log_file}")
    print("")
    
    print("-" * 80)
    print(f"SHELL 2 (RIGHT PANE): {shell_right_name}")
    print("-" * 80)
    if right_meta:
        stats = right_meta.get("statistics", {})
        duration = stats.get('duration_seconds', 'N/A')
        if isinstance(duration, float):
            duration = f"{duration:.2f}s"
        print(f"  Duration:       {duration}")
        print(f"  Input:          {stats.get('bytes_sent', 0)} bytes")
        print(f"  Output:         {stats.get('bytes_received', 0)} bytes")
        print(f"  Input Lines:    {stats.get('lines_input', 0)}")
        print(f"  Output Lines:   {stats.get('lines_output', 0)}")
    else:
        print("  (No metadata found)")
    
    log_file = log_dir / f"{shell_right_name}.log"
    print(f"  Log File:       {log_file}")
    print("")
    
    print("-" * 80)
    print("NEXT STEPS: Generate Production Pexpect Script")
    print("-" * 80)
    print("")
    print("  Use the logs from both shells to generate a standalone pexpect script")
    print("  that automates the interaction between two spawned processes.")
    print("")
    print(f"  Shell 1 Log: {log_dir / f'{shell_left_name}.log'}")
    print(f"  Shell 2 Log: {log_dir / f'{shell_right_name}.log'}")
    print("")
    print("  Production Script Features:")
    print("  - Two independent pexpect.spawn() children")
    print("  - Bi-directional communication (data exchange)")
    print("  - No tmux (pure pexpect automation)")
    print("  - Fully deterministic and reproducible")
    print("")


def main():
    parser = argparse.ArgumentParser(
        description="Start interactive dual-shell pexpect development session",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pexpect_interactive_start.py
  python3 pexpect_interactive_start.py --shell /bin/zsh
  python3 pexpect_interactive_start.py --name my_dev_session
        """,
    )
    parser.add_argument(
        "--shell",
        default="/bin/bash",
        help="Shell to spawn (default: /bin/bash)",
    )
    parser.add_argument(
        "--name",
        help="Session name (auto-generated with timestamp if not provided)",
    )
    parser.add_argument(
        "--log-dir",
        default="./.pexpect_sessions",
        help="Directory for log files (default: ./.pexpect_sessions)",
    )

    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    if args.name:
        session_name = args.name
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_name = f"dual_shell_{timestamp}"

    try:
        session = DualShellTmuxSession(
            shell=args.shell,
            log_dir=str(log_dir),
            session_name=session_name,
        )
        session.run()

    except KeyboardInterrupt:
        print("\nSession interrupted by user")
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        print("Make sure tmux is installed: apt-get install tmux", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
