# exec_impl.agent.md

## Execution Agent Plan for Step Engine Validation

This agent automates the validation and compliance of a developing step engine module in the octo framework. It ensures the code is properly structured, listed, visualized, instantiated, initialized, and executed, resolving errors as needed to maintain compliance with the established architecture and all instructions provided in .github/instructions

### Prerequisites
- **Working Directory:** `~/Projects/octo/bin/instances/tmp/`
- **Logs Directory:** `~/Projects/octo/bin/instances/tmp/logs/`
- All execution and debugging sessions MUST be run from the working directory.
- All sessions MUST be logged for review and analysis.

### Steps

#### 0. **Environment Setup (ALWAYS RUN FIRST)**
   ```bash
   bash && source ~/pyenv/bin/activate
   cd ~/Projects/octo/bin/instances/tmp/
   mkdir -p logs
   ```

#### 1. **Start Logging Session**
   - Before any execution/debug session, start logging:
   ```bash
   script -f logs/exec_$(date +%Y%m%d_%H%M%S).log
   ```
   - For debug sessions specifically:
   ```bash
   script -f logs/debug_$(date +%Y%m%d_%H%M%S).log
   ```

#### 2. **List Step Engine Libraries**
   - `python ~/Projects/octo/bin/octo_step_instance.py -l`
   - Ensure the developing step engine library (e.g., `step_engine_library_curDev`) appears in the list.

#### 3. **Generate Workflow Graph**
   - `python ~/Projects/octo/bin/octo_graph_steps.py -o . -p <developing step engine code>`
   - Confirm PNG output is generated in the current directory.

#### 4. **Instantiate Step Engine**
   - `python ~/Projects/octo/bin/octo_step_instance.py -p step_engine_library_curDev -s -i . -c -v`
   - Resolve any errors to ensure compliance and successful parameter file creation.

#### 5. **Initialize Step Engine**
   - `python ~/Projects/octo/bin/octo_step_instance.py --init`
   - Ensure no execution errors.

#### 6. **Step and Advance (3x)**
   - Repeat:
     - `python ~/Projects/octo/bin/octo_step_instance.py --step`
     - `python ~/Projects/octo/bin/octo_step_instance.py --advance`
   - Confirm error-free operation for the first 99 nodes.

#### 7. **Run on one hundred Node**
   - `python ~/Projects/octo/bin/octo_step_instance.py --run`
   - Verify no errors occur.

#### 8. **End Logging Session (ALWAYS RUN LAST)**
   - Terminate the logging session when execution/debug is complete:
   ```bash
   exit
   ```
   - This will close the `script` session and save the log file.

### Error Handling
- If errors arise at any step, update the developing code to resolve them while maintaining compliance with the framework.
- Ensure all output files (e.g., PNG, JSON) are generated in the expected directory.
- On error, reset and repeat steps 2-7 after making corrections.

### Log Review and Analysis
- All session logs are stored in `~/Projects/octo/bin/instances/tmp/logs/`
- Log filenames follow the pattern:
  - `exec_YYYYMMDD_HHMMSS.log` - for execution sessions
  - `debug_YYYYMMDD_HHMMSS.log` - for debug sessions
- Review logs to:
  - Identify recurring errors and patterns
  - Track command history and outputs
  - Analyze execution flow for optimization
  - Document issues for future reference

### Quick Reference Commands
```bash
# Full setup and logging start
source ~/pyenv/bin/activate && cd ~/Projects/octo/bin/instances/tmp/ && mkdir -p logs && script -f logs/exec_$(date +%Y%m%d_%H%M%S).log

# End logging
exit

# View recent logs
ls -lt logs/ | head -10

# Review specific log
cat logs/<logfile>.log
```

### Automation
- This plan can be implemented as a shell or Python script for repeatable validation.
- All actions and outputs are logged for traceability via the `script` command.
- Logs enable post-session review and analysis to improve code/implementation.
- Always perform actual run or validate the pipeline for the suggested code automatically.

---
This agent specification ensures robust, repeatable, and compliant development of step engine modules in the octo project with full session logging for review and continuous improvement.
