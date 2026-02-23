#!/bin/bash
# Script to generate framework-spec/pexpect-memory-schema.md
set -e

TARGET="framework-spec/pexpect-memory-schema.md"
DIR=$(dirname "$TARGET")

if [ ! -f "$DIR/.write_exception" ] && [ ! -f ".write_exception" ]; then
    echo "⚠️ Cannot write $TARGET — .write_exception missing"
    exit 1
fi

mkdir -p "$DIR"

cat > "$TARGET" <<'EOF'
# Pexpect Memory Schema

All structured knowledge stored under: pexpect-memory/

# Directory Structure
pexpect-memory/
    version.json
    prompt-patterns.json
    command-patterns.json
    error-signatures.json
    timing-model.json
    workflow-templates.json
    compatibility-matrix.json
    session-index.json
EOF

echo "✅ $TARGET generated successfully."