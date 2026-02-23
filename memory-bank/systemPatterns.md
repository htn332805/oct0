# System Patterns

## Step Node Design

- Atomic, single-responsibility step nodes.
- Each step node defines node/arrow graph dictionaries, params, results, and lifecycle methods.

## Parameter Store

- Use `octo_step_engine_parameters` + `octo_lock_json` for shared state.
- Store parameters in `.octo_step_engine_parameters.json` in the working directory.

## Dynamic Discovery

- Step node modules follow `step_node_module_py_{name}.py` naming.
- Modules export `step_node_class_list` for discovery.

## Graph Visualization

- Use `octo_graph_steps.py` to render node/arrow graphs (DOT/PNG).

## Tmux Automation Pattern

- Create a session, split a 4×4 grid, title panes, pipe logs, then send commands.
- `step_engine_library_tmux_layout` is the current reference implementation.
