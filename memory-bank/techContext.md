# Tech Context

## Languages & Tools

- Python 3
- Shell (bash)
- tmux
- filelock (for JSON locking)
- pygraphviz (graph rendering)
- pyfiglet (optional ASCII banners)

## Repo Layout

- `bin/`: CLI utilities, step engine runtime, docs
- `bin/modules/`: core modules and step node base
- `bin/modules/step_engine_library/`: step node libraries
- `bin/instances/`: demos and environment-specific scripts
- `memory-bank/`: persistent project knowledge

## Execution Constraints

- Run commands from `bin/instances/tmp`.
- Activate venv at `~/pyenv/bin/activate` before Python execution.
