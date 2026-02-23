#!/bin/bash
# Usage: ./generate_prompt.sh SINGLE_FILE src/file.py output_name
# Usage: ./generate_prompt.sh MULTIPLE_FILES "src/a.py,src/b.py" output_name
# Usage: ./generate_prompt.sh FOLDER_RECURSIVE bin/utils/ output_name

SCOPE_TYPE=$1
TARGET_PATHS=$2
OUTPUT_NAME=$3
TEMPLATE="/home/tester/Projects/octo/.github/prompts/code_analysis_report.prompt.md"

# Determine file types
if [[ $TARGET_PATHS == *.py ]]; then
    FILE_TYPES=".py"
elif [[ $SCOPE_TYPE == "FOLDER_RECURSIVE" ]]; then
    FILE_TYPES=".py,.sh,.sed,.awk,.tcl"
else
    FILE_TYPES=".py"
fi

# Determine report type
if [[ $SCOPE_TYPE == "SINGLE_FILE" ]]; then
    REPORT_TYPE="SINGLE"
else
    REPORT_TYPE="PER_FILE"
fi

# Generate custom prompt
OUTPUT_FILE="/home/tester/Projects/octo/.github/prompts/${OUTPUT_NAME}.prompt.md"
cp "$TEMPLATE" "$OUTPUT_FILE"

# Simple variable replacement (use sed or envsubst)
sed -i "s|{{SCOPE_TYPE}}|$SCOPE_TYPE|g" "$OUTPUT_FILE"
sed -i "s|{{TARGET_PATHS}}|$TARGET_PATHS|g" "$OUTPUT_FILE"
sed -i "s|{{FILE_TYPES}}|$FILE_TYPES|g" "$OUTPUT_FILE"
sed -i "s|{{REPORT_TYPE}}|$REPORT_TYPE|g" "$OUTPUT_FILE"
sed -i "s|{{OUTPUT_NAME}}|$OUTPUT_NAME|g" "$OUTPUT_FILE"

echo "Generated: $OUTPUT_FILE"
echo "Use in Copilot: @workspace Use $OUTPUT_FILE"
