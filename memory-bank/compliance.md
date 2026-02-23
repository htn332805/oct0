# Compliance Constraints


- All step nodes must be atomic and single-responsibility.
- Shared state must use the step engine parameters utility.
- Dynamic module loading must follow strict naming conventions.
- No direct file access for shared state.
- No monolithic step node classes.
- All workflows must be graph-based and support dynamic composition.

## Naming and Loading Rules

- Step node modules must be named `step_node_module_py_{name}.py`.
- Modules must export `step_node_class_list` with all class names in that module.
- Step node classes must keep `module_name_string` and `node_step_name_string` in sync.

## Runtime Behavior Rules

- Do not use `breakpoint()` or `quit()` in non-interactive execution paths.
- Avoid wildcard imports; use explicit imports.
- Use `octo_step_engine_parameters` + `octo_lock_json` for all shared state.

## Step Node Core Component Requirements

Each step node class must define the following core components:
1. `step_node_graph_dict` — Node graph dictionary for workflow integration and visualization.
2. `step_arrow_graph_dict` — Arrow/transition graph dictionary for workflow routing.
3. `step_node_params_dict_init` — Initial parameters dictionary for the node.
4. `step_node_results_dict_init` — Initial results dictionary for the node.
5. `name` attribute — Human-readable name for the node.
6. `description` attribute — Description of the node's purpose.
7. `__init__` method — Constructor for setting up the node.
8. `step_entry` method — Logic to execute on node entry.
9. `step_exit` method — Logic to execute on node exit.
10. `step_execute` method — Main execution logic for the node.
11. `step_advance` method — Determines the next step or transition.

All step node classes must implement these components to ensure compliance, composability, and maintainability within the Octo step engine framework.
