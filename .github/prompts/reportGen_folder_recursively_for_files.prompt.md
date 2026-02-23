# SPARC Code Analysis Report Generator

You are the SPARC Orchestrator for this repository.

## MISSION
Create comprehensive analysis for all code files recursively within the utilities folder (Python, Shell, AWK, Sed, Tcl).

---

## INPUT CONFIGURATION

**Analysis Scope:** FOLDER_RECURSIVE

**Target Path(s):**
bin/utils/

**File Types to Include:** .py,.sh,.sed,.awk,.tcl
<!-- Or use * for all code files -->

**Output Location:** bin/docs/analysis/utils_complete_2026-02-07/

**Report Structure:** PER_FILE
<!-- Creates hierarchical structure:
  bin/docs/analysis/utils_complete_2026-02-07/
    ├── PROJECT_ANALYSIS.md (top-level summary)
    ├── python_tools/
    │   ├── README.md (module summary)
    │   ├── logger.py.md
    │   └── config_parser.py.md
    ├── shell_scripts/
    │   ├── README.md
    │   ├── deploy.sh.md
    │   └── backup.sh.md
    └── data_processors/
        ├── README.md
        ├── transform.awk.md
        └── sanitize.sed.md
-->

---

[Rest of template with {{#if FOLDER_RECURSIVE}} sections activated]

## READY?
Acknowledge this mission and confirm:
- Target: bin/utils/ (recursive)
- Scope: FOLDER_RECURSIVE
- File types: .py, .sh, .sed, .awk, .tcl
- Report type: PER_FILE (hierarchical + summaries)
- Output: bin/docs/analysis/utils_complete_2026-02-07/
