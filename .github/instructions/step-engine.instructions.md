---
paths:
  - "modules/**"
  - "bin/modules/step_engine_library/*/*.py"
---

# Instructions for Octo step engine code

- Do not bypass the step engine parameter system when sharing state.
- Follow the existing patterns for `step_node_graph_dict` and `step_arrow_graph_dict`.
- When adding a new step node class:
  - Place it in `step_node_module_py_<name>.py`.
  - Ensure it is atomic and single-purpose.
  - Add clear logging where appropriate using the project logger.
- When changing workflows, cross-check that the Memory Bank documentation matches the new graph structure.
