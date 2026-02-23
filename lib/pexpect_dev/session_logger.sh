#!/bin/bash
# Transparent session logger using the `script` command.
# Produces a plain-text log (ANSI stripped) plus JSON metadata for analysis.

SESSION_ID="session_$(date +%Y%m%d_%H%M%S)"
LOG_DIR="./.sessions"
LOG_FILE="${LOG_DIR}/${SESSION_ID}.log"
METADATA_FILE="${LOG_DIR}/${SESSION_ID}.json"

mkdir -p "$LOG_DIR"

echo "════════════════════════════════════════════════"
echo "🚀 Starting Logged Session"
echo "════════════════════════════════════════════════"
echo "   Session ID: $SESSION_ID"
echo "   Log File:   $LOG_FILE"
echo ""
echo "   All your commands and output will be logged."
echo "   Type 'exit' or press Ctrl+D to end session."
echo "════════════════════════════════════════════════"
echo ""

# Create initial metadata
cat > "$METADATA_FILE" <<EOF
{
  "session_id": "$SESSION_ID",
  "shell": "${SHELL:-/bin/bash}",
  "start_time": "$(date -Iseconds)",
  "log_file": "$LOG_FILE",
  "user": "$USER",
  "hostname": "$(hostname)"
}
EOF

# Start script session (quiet mode)
# This records everything printed in the shell into $LOG_FILE.
script -q "$LOG_FILE"
# Strip ANSI escape sequences from the log in-place using Python
python3 - "$LOG_FILE" <<'PYEOF'
import re
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("Usage: python - <log_file>")

log_path = Path(sys.argv[1])
text = log_path.read_text(encoding="utf-8", errors="replace")

# Regex to remove ANSI escape sequences. [web:2][web:3]
ansi_re = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
clean = ansi_re.sub("", text)

log_path.write_text(clean, encoding="utf-8")
PYEOF

echo ""
echo "════════════════════════════════════════════════"
echo "📊 Session Ended: $SESSION_ID"
echo "════════════════════════════════════════════════"

# Update metadata with end time, duration, and log stats
python3 - <<PYEOF
import json
from datetime import datetime
from pathlib import Path

metadata_file = Path("${METADATA_FILE}")
log_file = Path("${LOG_FILE}")

with metadata_file.open("r", encoding="utf-8") as f:
    data = json.load(f)

data["end_time"] = datetime.now().isoformat()

start = datetime.fromisoformat(data["start_time"])
end = datetime.fromisoformat(data["end_time"])
duration = (end - start).total_seconds()

data["duration_seconds"] = duration
data["log_size_bytes"] = log_file.stat().st_size if log_file.exists() else 0

if log_file.exists():
    with log_file.open("r", encoding="utf-8", errors="replace") as f:
        data["log_lines"] = sum(1 for _ in f)
else:
    data["log_lines"] = 0

with metadata_file.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"   Duration:   {int(duration // 60)}m {int(duration % 60)}s")
print(f"   Log Lines:  {data['log_lines']}")
print(f"   Log Size:   {data['log_size_bytes']} bytes")
print(f"   Location:   {log_file}")
print("")
print("To analyze this session:")
print(f"   python -m lib.pexpect_dev.session_analyzer {log_file}")
PYEOF

echo "════════════════════════════════════════════════"
