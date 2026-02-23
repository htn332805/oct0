import json
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any


@dataclass
class ResumePoint:
    """
    Represents a checkpoint from which a pexpect session can be resumed.

    - timestamp: When the checkpoint was recorded (ISO 8601 string).
    - name: Logical name for the checkpoint (e.g., "after_login").
    - spawn_command: The original command used to spawn the pexpect child.
    - spawn_args: Dict containing 'args' and 'env' for respawning.
    - last_pattern: Value of child.after at checkpoint time (optional).
    - buffer_snapshot: Recent output (child.before) for context.
    - session_vars: Arbitrary user-defined state at checkpoint.
    """
    timestamp: str
    name: str
    spawn_command: str
    spawn_args: Dict[str, Any]
    last_pattern: Optional[str]
    buffer_snapshot: str
    session_vars: Dict[str, Any]

class PexpectSessionManager:
    """
    Manages pexpect session checkpoints and logging for later analysis.

    - Writes logs in a format compatible with session_analyzer.py:
      [YYYY-MM-DD HH:MM:SS.mmm] [TYPE] [SESSION_ID] content
    - Stores in-memory ResumePoint objects that can be turned into
      standalone resume scripts.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.resume_points: Dict[str, ResumePoint] = {}
        self.log_file = Path(f".pexpect_sessions/{session_id}.log")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log(self, entry_type: str, content: str) -> str:
        """
        Log a manager-level event in a standardized format:

        [TIMESTAMP] [ENTRY_TYPE] [SESSION_ID] content
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        line = f"[{timestamp}] [{entry_type}] [{self.session_id}] {content}\n"
        with self.log_file.open("a", encoding="utf-8") as f:
            f.write(line)
        return line

    def marker(self, name: str) -> None:
        """
        Convenience method to log a MARKER entry, which will be
        interpreted by the analyzer as a phase boundary.
        """
        self.log("MARKER", name)

    def save_checkpoint(self, name: str, spawn_obj, session_vars: Dict[str, Any] = None) -> ResumePoint:
        """
        Save a checkpoint from a live pexpect spawn object.

        Parameters:
            name:          Logical name for this checkpoint (e.g., "after_login").
            spawn_obj:     A pexpect.spawn (or compatible) instance.
            session_vars:  Arbitrary dict of state you want to serialize alongside.

        This will:
        - Capture the spawn command and args/env.
        - Capture last_pattern (child.after) and buffer_snapshot (child.before).
        - Store a ResumePoint in memory and emit RESUME_POINT entries in the log.
        """
        checkpoint = ResumePoint(
            timestamp=datetime.now().isoformat(),
            name=name,
            spawn_command=getattr(spawn_obj, "command", ""),
            spawn_args={
                "args": getattr(spawn_obj, "args", []),
                "env": getattr(spawn_obj, "env", {}),
            },
            last_pattern=getattr(spawn_obj, "after", None),
            buffer_snapshot=(getattr(spawn_obj, "before", "") or ""),
            session_vars=session_vars or {},
        )

        self.resume_points[name] = checkpoint

        # Log the checkpoint in a way that the analyzer can treat as a structural boundary.
        self.log("RESUME_POINT", f"=== {name} ===")
        self.log("RESUME_POINT_DATA", json.dumps(asdict(checkpoint)))

        return checkpoint

    def get_resume_script(self, checkpoint_name: str) -> str:
        """
        Generate a standalone Python script to resume from a checkpoint.

        The script:
        - Re-spawns the original command with recorded args.
        - Documents the last_pattern and buffer_snapshot for reference.
        - Leaves TODOs for re-establishing auth/state as needed.
        """
        cp = self.resume_points.get(checkpoint_name)
        if not cp:
            raise ValueError(f"No checkpoint named '{checkpoint_name}'")

        script = f"""#!/usr/bin/env python3
\"\"\"Resume pexpect session from checkpoint: {cp.name}

Original session: {self.session_id}
Recorded at: {cp.timestamp}

This script re-spawns the original command and gives you a fresh
pexpect child to continue automation or debugging from this stage.
\"\"\"

import pexpect


def resume_from_checkpoint():
    \"\"\"Resume pexpect session from checkpoint: {cp.name}\"\"\"
    child = pexpect.spawn(
        command={repr(cp.spawn_command)},
        args={repr(cp.spawn_args.get("args", []))},
        encoding="utf-8",
    )

    # Last known pattern (child.after) at checkpoint time:
    # {repr(cp.last_pattern)}

    # Buffer snapshot (child.before) at checkpoint time:
    # {repr(cp.buffer_snapshot)}

    # TODO:
    # - Re-establish any required authentication.
    # - Recreate environment variables or working directory if needed.
    # - Fast-forward the session state to match the original context.

    return child


if __name__ == "__main__":
    child = resume_from_checkpoint()
    print("Session resumed from checkpoint: {cp.name}")
    # You can now interact with `child` (e.g., child.sendline(...), child.expect(...))
"""
        return script

# Example usage (for reference only, not executed here):
#
# import pexpect
# from pexpect_session_manager import PexpectSessionManager
#
# mgr = PexpectSessionManager(session_id="ssh_exp_01_auto")
# child = pexpect.spawn("ssh user@host", encoding="utf-8")
#
# # ... login, expect prompts, etc. ...
#
# mgr.marker("AFTER_LOGIN_PHASE")
# mgr.save_checkpoint("after_login", child, session_vars={"user": "user"})
#
# # Later, if you want a resume script:
# script_text = mgr.get_resume_script("after_login")
# Path("resume_after_login.py").write_text(script_text, encoding="utf-8")
