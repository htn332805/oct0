# Pexpect Automation Governance Specification

# Architecture Overview
Interactive Development Layer (tmux optional)
↓
Raw Logs
↓
AI Extraction Phase
↓
pexpect-memory/
↓
Standalone Production Scripts

# Development Layer
- Observe CLI behavior
- Identify timing patterns
- Detect errors
- tmux allowed only here

# Production Layer
- Pure pexpect
- No tmux
- Fully standalone

# Determinism Requirements
- Explicit expect patterns
- Configurable timeouts
- Fail safely
- Log consistently

# Backward Compatibility
- Load pexpect-memory knowledge
