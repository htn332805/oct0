
# Step Node Module Generation Instructions

---
applyTo: "bin/modules/step_engine_library/**/step_node_module_py_*.py"
description: "Core data model patterns"
---

All generated step node modules (e.g., `bin/modules/step_engine_library/step_engine_library_XXX/step_node_module_py_{name}.py`) must comply with the following requirements. These are mandatory for compliance and maintainability, based on feature identification and engineering analysis of the Octo step engine codebase.



## 1. Core Compliance Requirements

Every step node class must:

- **Inherit from `stepnode_baseclass`** (from `modules/stepnode_baseclass.py`).
- **Filename**: Must match `step_node_module_py_{name}.py`.
- **Atomic, single-responsibility**: Each class must represent a single, atomic, granular step in a workflow.
- **Define all required attributes and methods:**
    - `step_node_graph_dict` (graphviz-compatible node attributes)
    - `step_arrow_graph_dict` (graphviz-compatible edge attributes)
    - `step_node_params_dict_init` (initial parameters)
    - `step_node_results_dict_init` (initial results)
    - `name` (short human-readable)
    - `description` (purpose)
    - `__init__`, `step_entry`, `step_exit`, `step_execute`, `step_advance`
- **Parameter/result schema**: Each node must define its own parameter/result initialization for atomicity and composability.
- **Parameter management**: All shared state must be managed via the provided parameter management utility (`octo_step_engine_parameters`), ensuring atomic file access and locking. Never access shared files directly.
- **Graph-based workflow integration**: All nodes must define their place in the workflow graph and their outgoing transitions.
- **Module-level `step_node_class_list`**: Each module must list its step node classes for dynamic discovery.
- **Verbose flag**: All nodes must support a `verbose_flag` for debug output.
- **Banner/branding**: Only `octo_banner_module` may be used for banner output. Do not use custom banners or other banner modules.
- **Debugging/logging**: Use the project logger or Python `logging` for all logging. Use `icecream` only if project-wide approved.



## 2. Implementation Guidelines


### Methods
- `__init__(self, ...)`: Initialize with required parameters.
- `step_entry(self)`: Logic to execute on node entry.
- `step_exit(self)`: Logic to execute on node exit.
- `step_execute(self)`: Main execution logic for the node. **You must ensure this method is actually called during the workflow step.**
- `step_advance(self)`: Determines the next step or transition.
- Optional: `validate(self, ...)`, `cleanup(self, ...)` for pre/post logic.

### Execution and Logging Requirements
- **Ensure that `step_execute` is actually called during the workflow step.**
- **Check if the workflow engine suppresses or redirects stdout from step nodes.**
- **Add logging in `step_entry`, `step_exit`, and `step_execute` to confirm which methods are called.**
- **Timestamp Printout (MANDATORY):** Every `step_execute` method must print a timestamp at the start of execution. Use the following pattern:
  ```python
  from datetime import datetime
  
  def step_execute(self):
      print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Executing: {self.__class__.__name__}")
      # ... rest of execution logic ...
  ```


### File/Parameter Access
- Always use file lock and parameter management utilities from `bin.octo_step_engine_parameters` (see `bin/scriptlet_step_engine_params.py`).
- Never read/write shared files directly—always use provided context managers/utilities.
- All shared state must be managed via the parameter manager for safe concurrent access.

### Integration
- Import and use utility, logging, or orchestration modules as needed.
- Use the project logger or Python `logging` for all logging.
- For cross-step communication, use the parameter management system, not direct variable passing.
- Only use `octo_banner_module` for banner/branding output.

### Dynamic Module Loading
- Ensure class and file naming follow conventions for dynamic discovery.
- Avoid hard-coded imports; use `importlib` or similar for dynamic loading.
- Register your class if a registry is used, or ensure discoverability by naming.
- Use consistent naming conventions for graph/arrow dict keys across modules.

### Atomic Step Node Design
- Each class should do one thing (e.g., fetch data, validate input, write output).
- Compose complex workflows by sequencing atomic step nodes.

### DOs
- Break down complex tasks into small, single-responsibility step node classes.
- Use file locks and parameter management utilities for all shared state.
- Log key actions and errors.
- Write clear, minimal step node methods.
- Inherit from `stepnode_baseclass` for all step node classes.
- Use only `octo_banner_module` for banners.
- Document any advanced shell/tmux/pexpect logic for maintainability.
- Standardize graph/arrow dict key naming across modules.

### DON'Ts
- Don’t access shared files without locking.
- Don’t combine multiple unrelated actions in one step node.
- Don’t use global state or direct inter-class variable passing.
- Don’t use custom banners or banner modules other than `octo_banner_module`.



## 3. Template Code Snippets

### Example Step Node: SLDP Start (from swimssldp)
```python
import subprocess
from datetime import datetime
from stepnode_baseclass import stepnode_baseclass
from octo_banner_module import octopusbanner
from octo_step_engine_parameters import octo_step_engine_parameters
import os, json

shared = octo_step_engine_parameters()

from stepnode_baseclass import stepnode_baseclass

# list of step_classes in this file:
step_node_class_list = [ "step_node_class_<shortname>"]

class step_node_class_<shortname>(stepnode_baseclass):
    step_node_graph_dict = {
        "step_node_class_<shortname>" : {
            "module_name_string" : "step_node_module_py_<shortname>",
            "node_step_name_string" : "step_node_class_<shortname>",
            "dg_node_attr_dict" : {
                "color" : "green",
                "shape" : "rectangle",
                "style" : "filled",
                "fillcolor" : "pink",
            },
            "first_node_step_bool" : 0,
            "active_node_step_bool" : 1,
            "node_entry_breakpoint" : 0,
            "node_exit_breakpoint" : 0,
            "skip_step_node_execute_bool" : 0,
        },
    }
    step_arrow_graph_dict = {
        ### This step_arrow_graph_dict_key is returned in function step_advance() below:
        "step_arrow_graph_list_key_success_path" : {
            "module_name_string" : "step_node_module_py_<shortname>",
            "arrow_step_name_string" : "step_node_class_<shortname>",
            "dg_edge_attr_dict" : {
                "color" : "lightblue",
            },
            "active_arrow_step_bool" : 1,
        },
        ### This step_arrow_graph_dict_key is returned in function step_advance() below:
        "step_arrow_graph_list_key_failure_path" : {
            "module_name_string" : "step_node_module_py_<shortname>",
            "arrow_step_name_string" : "step_node_class_<shortname>",
            "dg_edge_attr_dict" : {
                "color" : "red",
            },
            "active_arrow_step_bool" : 1,
        },
        ### This step_arrow_graph_dict_key is returned in function step_advance() below:
        "step_arrow_graph_list_key_custom_path" : {
            "module_name_string" : "step_node_module_py_<shortname>",
            "arrow_step_name_string" : "step_node_class_<shortname>",
            "dg_edge_attr_dict" : {
            },
            "active_arrow_step_bool" : 0,
        },
    }
    step_node_params_dict_init = {
        "step_node_class_<shortname>" : {
            "step_node_param_key_<some_key>" : "some string value",
        },
    }
    step_node_results_dict_init = {
        "step_node_class_<shortname>" : {
            "step_results_key_last_status" : "SUCCESS",
            "step_results_key_<some_key>" : "some result value",
        },
    }
    def __init__(self, name, verbose_flag = False):
    	# super().__init__(name):
        self.name = name
        self.description = "step_node_class_<shortname>"
        self.verbose_flag = verbose_flag
        if self.verbose_flag == True :
            # print("\t\tStep_Init(" + self.name + ")")
            pass
    def step_entry(self):
        print(octopusbanner("CLEAR-PORT").banner_result)
        if self.verbose_flag:
            print("\t\tStep_Entry", self.name, self.description)
        accept_entry_step = 0
        return accept_entry_step
    def step_exit(self):
        if self.verbose_flag:
            print("\t\tStep_Exit", self.name, self.description)
        exit_state = 0
        return exit_state
    def step_advance(self):
        if self.verbose_flag == True :
            print("\t\tStep_Advance(" + self.name + ", " + self.description + ")")
        ### The step_arrow_graph_dict_key above is returned in this function:
        # next_step_arrow_graph_dict_key = "step_arrow_graph_list_key_step_003"
        next_step_arrow_graph_dict_key = "step_arrow_graph_list_key_success_path"
        return next_step_arrow_graph_dict_key
```

## 4. Troubleshooting Dynamic Loading
- If your module isn’t discovered, check naming conventions and class visibility.
- Use `importlib` for dynamic imports if needed.
- Ensure your class is not nested or private.

---
### Compliance Checklist (Summary)
- [ ] Inherits from `stepnode_baseclass`
- [ ] Defines all required attributes and methods (see Core Compliance Requirements)
- [ ] Uses only `octo_banner_module` for banners
- [ ] Manages all shared state via parameter manager
- [ ] Follows atomic, single-responsibility design
- [ ] Uses graph/arrow dicts with graphviz-compatible attributes
- [ ] Has module-level `step_node_class_list`
- [ ] Uses consistent naming conventions for graph/arrow keys
- [ ] Documents advanced logic if present
- [ ] The last node should be return "COMPLETE"
- [ ] `step_execute` prints timestamp at start of execution

For further details, see `bin/docs/step_node_module_compliance_spec.md`, `modules/stepnode_baseclass.py`, and `bin/scriptlet_step_engine_params.py`.
