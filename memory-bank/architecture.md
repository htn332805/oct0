# Architecture Guidance (Current Implementation)

## High-Level Architecture

- **Step-engine orchestration:** `octo_step_instance.py` drives execution using a JSON-backed parameter store.
- **Dynamic node loading:** `octo_step_lib.py` discovers and imports `step_node_*.py` modules and instantiates classes listed in `step_node_class_list`.
- **Shared state:** `octo_step_engine_parameters.py` wraps atomic JSON access via `octo_lock_json.py` (file locking with `FileLock`).
- **Workflow graphs:** node and arrow dictionaries define flow; `octo_graph_steps.py` renders the graph with PyGraphviz.
- **Scaffolding:** `dot_to_shorthand.py` converts DOT → shorthand CSV, and `octo_shorthand.py` converts shorthand CSV → step-node module templates.

## Key Subsystems

- **Step Engine Core**
	- `octo_step_instance.py` (runtime loop)
	- `octo_step_lib.py` (library discovery & load)
	- `octo_step_engine_parameters.py` (param schema & IO)
	- `octo_lock_json.py` (atomic JSON access)

- **Visualization & Generation**
	- `octo_graph_steps.py` (graphviz output)
	- `dot_to_shorthand.py` + `octo_shorthand.py` (scaffold pipeline)

- **Operational Utilities**
	- `scriptlet_step_engine_params.py` (CLI param inspection/updates)
	- `octo_banner.py` + `octo_banner_module.py` (ASCII banner)

- **Automation Examples**
	- `step_engine_library_tmux_layout` provides step nodes for tmux session lifecycle and logging.
	- `instances/*/tmux_predefined_layout.py` scripts demonstrate 4×4 grid creation and pane commands.

## Hard Constraints

- Shared state must go through the parameter utility.
- Step nodes are atomic and single-responsibility.
- Dynamic module naming must follow the `step_node_module_py_{name}.py` convention.