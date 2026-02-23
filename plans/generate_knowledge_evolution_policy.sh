#!/bin/bash
# Script to generate framework-spec/knowledge-evolution-policy.md
set -e

TARGET="framework-spec/knowledge-evolution-policy.md"
DIR=$(dirname "$TARGET")

if [ ! -f "$DIR/.write_exception" ] && [ ! -f ".write_exception" ]; then
    echo "⚠️ Cannot write $TARGET — .write_exception missing"
    exit 1
fi

mkdir -p "$DIR"

cat > "$TARGET" <<'EOF'
# Knowledge Evolution Policy

# 1. Raw Logs Are Immutable
- Logs under logs/ are ground truth
- Never edited or rewritten

# 2. Extraction Phase
- Extract prompt regex
- Stable command flows
- Error signatures
- Timing metrics
- Convert into structured JSON

# 3. Schema Validation
- Validate JSON structure
- Increment version on modification

# 4. Drift Detection
- Flag conflicting session behavior
- Require explicit approval

# 5. Backward Compatibility Rule
- Preserve existing workflows and prompt patterns

# 6. Memory-Bank Protection
- memory-bank/ must remain untouched
EOF

echo "✅ $TARGET generated successfully."