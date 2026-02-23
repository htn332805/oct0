# Project Brief

## Purpose

Provide a modular step-based workflow engine to automate operational tasks (e.g., tmux layouts, device connections, logging, report generation) using composable step nodes and graph-based workflows.

## Scope

- Step-engine runtime and utilities under `bin/` and `bin/modules/`.
- Dynamic step node libraries under `bin/modules/step_engine_library/`.
- Instance-specific automation and demos under `bin/instances/`.

## Non-Goals

- This repository is not a general-purpose scheduler or CI system.
- It is not intended to run untrusted code without review.
