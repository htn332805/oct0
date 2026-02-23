# Approved Implementation Patterns

## Step Node Pattern
- Each step node class inherits from the base class and implements a single responsibility.
- Step nodes are composed into workflows via engine scripts.
- Use the step engine parameters utility for all shared state.

## Parameter Store Pattern
- Read/write parameters using `octo_step_engine_parameters` which wraps `octo_lock_json`.
- Store instance parameters in `.octo_step_engine_parameters.json` in the working directory.

## Tmux Automation Pattern
- For tmux layouts, prefer reusable helper scripts (see `instances/*/tmux_predefined_layout.py`).
- Use a fixed 4×4 split strategy and name panes for traceable logging.
- For logging, use `tmux pipe-pane` with deterministic log names.

## Optional Import Pattern

See [patterns/optional_import.md](patterns/optional_import.md) for the full example and explanation.

This pattern allows code to gracefully handle optional dependencies by attempting to import a module or class in a try/except block. If the import fails, the symbol is set to None, and the code can check for its presence before using it. This is useful for supporting optional features or providing fallback behavior.

## Dynamic Module Loading
- Step node modules must follow strict naming: step_node_module_py_{name}.py
- Engine scripts discover and load modules dynamically based on naming.

## Graph-Based Workflow
- Workflows are described as graph dictionaries mapping step nodes and transitions.
- Supports dynamic, visualizable workflows.

## Shell Integration
- Shell scripts in bin/ and instances/ may be invoked by Python modules for system-level tasks.
- Data/configuration flows from instances/ to bin/ and modules/.

Forbidden:
- Direct file access for shared state.
- Monolithic step node classes.
- Unapproved module naming.