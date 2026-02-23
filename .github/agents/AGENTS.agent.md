# SPARC Agents – Mission Guide for GitHub Copilot

This repository uses a **multi‑agent setup** for GitHub Copilot.  
Each agent has a clear role (specification, architecture, coding, testing, debugging, security, docs, integration, monitoring, optimization, orchestration, and onboarding) and is defined in a `.agent.md` file under `.github/agents/`.[web:104][web:98]

This document explains:

- What each agent does.
- When to use it.
- How **Boomerang** and the **SPARC Orchestrator** coordinate the rest.

Use this as both a **human onboarding guide** and a **signal to Copilot** about how to behave in this workspace.[web:104]

---

## 1. How to use these agents

You can use these agents in **VS Code + GitHub Copilot**:

- Each agent has a persona file like `.github/agents/architect.agent.md`.
- In Copilot Chat:
  - Pick the agent from the agent list, or
  - Say which agent you want to act as (for example, “Act as the architect agent defined in `.github/agents/architect.agent.md` for this task.”).

General usage pattern:

1. **Start with orchestration**  
   - For “what should we do and in what order?” use:
     - `sparc_orchestrator` for SPARC‑shaped, end‑to‑end flows.
     - `boomerang` for multi‑agent “mission control” across all roles.

2. **Let orchestrators assign work**  
   - They will suggest which specialist agents to call next and give you copy‑pasteable prompts.

3. **Run specialists in sequence or parallel**  
   - Example:
     - `spec-pseudocode` → `architect` → `code` → `tdd` → `security-review` → `docs-writer` → `integration` → `post-deployment-monitoring-mode` → `refinement-optimization-mode`.

4. **Keep tasks small and safe**
   - Prefer many small, focused agent calls over one giant ask.
   - Never hard‑code secrets or environment variables.
   - Aim for files under ~500 lines where practical.
   - Ask every agent to end with a short **completion summary** (what they did, key files, next steps).

---

## 2. Agent catalog

You have the following agents defined via `.github/agents/*.agent.md`:

| Agent name                      | File                                         | Primary role                                           | When to use it                                             |
|---------------------------------|----------------------------------------------|--------------------------------------------------------|------------------------------------------------------------|
| SPARC Orchestrator             | `.github/agents/sparc_orchestrator.agent.md`       | Designs full SPARC workflows end‑to‑end               | Large goals you want to take from idea → deploy‑ready     |
| Boomerang                      | `.github/agents/boomerang.agent.md`                | Mission‑control across all agents                     | Multi‑agent planning, subtask design, and routing         |
| SPARC Tutorial                 | `.github/agents/tutorial.agent.md`                 | Onboarding & education                                | When you or teammates need a guided tour of SPARC         |
| SPARC Ask                      | `.github/agents/sparc_ask.agent.md`                | Task‑formulation & question routing                   | When a request is vague and you need help shaping prompts |
| Spec & Pseudocode              | `.github/agents/spec-pseudocode.agent.md`          | Specs, user stories, acceptance criteria, pseudocode  | Clarify requirements before coding                        |
| Architect                      | `.github/agents/architect.agent.md`                | Architecture, components, API & data‑flow boundaries  | When you need structure, diagrams, or system design       |
| Code                           | `.github/agents/code.agent.md`                     | Implementation & refactors (env‑safe, modular)        | When it’s time to write or refactor code                  |
| TDD                            | `.github/agents/tdd.agent.md`                      | Test planning, test‑first dev, coverage               | Before/alongside coding and for regression tests          |
| Debug                          | `.github/agents/debug.agent.md`                    | Runtime issues & performance investigation            | When there’s a failing test, error, or slowdown           |
| Security Review                | `.github/agents/security-review.agent.md`          | Secrets, exposure and security hardening              | Any time you touch auth, data access, or external APIs    |
| Docs Writer                    | `.github/agents/docs-writer.agent.md`              | Markdown docs (READMEs, how‑tos, runbooks)            | After designs/changes that need explanation               |
| Integration                    | `.github/agents/integration.agent.md`              | Wiring, environment, and end‑to‑end cohesion          | When pieces must be glued into a working system           |
| Deployment Monitor             | `.github/agents/post-deployment-monitoring-mode.agent.md` | Post‑deploy metrics, logs, and regressions   | When planning or reviewing production behavior            |
| Optimizer / Refiner            | `.github/agents/refinement-optimization-mode.agent.md` | Refactors, modularity, and performance          | When code “works” but needs cleanup or speedups           |

These roles map well onto recommended multi‑agent patterns: planners, specialists, reviewers, and integrators working under a higher‑level orchestrator.[web:193][web:208]

---

## 3. Recommended workflows

Here are three “happy‑path” flows you and Copilot can follow.

### 3.1 New feature: idea → deploy‑ready

Use when you want to add a non‑trivial feature.

1. **High‑level plan** – `sparc_orchestrator`
   - Ask it to design a SPARC‑shaped plan (Specification → Pseudocode → Architecture → Refinement → Completion) and map each step to agents.

2. **Work decomposition** – `boomerang`
   - Take that plan and ask Boomerang to break it into small, concrete subtasks with prompts for each specialist.

3. **Specification & Pseudocode** – `spec-pseudocode`
   - Clarify user stories, acceptance criteria, and logic flows.

4. **Architecture** – `architect`
   - Design components, APIs, data flows, and boundaries.

5. **Implementation & Tests** – `code` + `tdd`
   - `tdd`: define tests and coverage goals.
   - `code`: implement or refactor while respecting env‑safety and file‑size constraints.

6. **Debug & Security** – `debug` + `security-review`
   - `debug`: chase down any failing tests or runtime issues.
   - `security-review`: inspect for secrets, insecure patterns, and misconfigurations.

7. **Docs & Integration** – `docs-writer` + `integration`
   - `docs-writer`: produce or update READMEs and usage docs.
   - `integration`: wire components, configs, and pipelines.

8. **Post‑deploy & Optimization** – `post-deployment-monitoring-mode` + `refinement-optimization-mode`
   - Monitor performance and errors.
   - Propose refactors/optimizations based on real behavior.

Throughout, ask each agent to end with a short **“what I did / what’s next”** summary so orchestrators can keep track of progress.

---

### 3.2 Bug or incident workflow

Use when something breaks or slows down.

1. **Orchestration** – `boomerang`
   - Describe the incident (what broke, when, any error messages).
   - Boomerang designs a small workflow centered on `debug` and `architect`, with follow‑ups for `code`, `tdd`, `docs-writer`, and `post-deployment-monitoring-mode`.

2. **Architecture sanity check** – `architect`
   - Review how the affected part is wired and flag structural risk areas.

3. **Root cause analysis** – `debug`
   - Investigate logs, failing tests, or symptoms to propose likely root causes and candidate fixes.

4. **Fix & tests** – `code` + `tdd`
   - Implement the minimal fix and add/update tests to prevent regressions.

5. **Docs & monitoring** – `docs-writer` + `post-deployment-monitoring-mode`
   - Document the incident and resolution.
   - Decide what to monitor to catch it earlier next time.

---

### 3.3 Refactor & optimization campaign

Use when code works but is messy, slow, or too big.

1. **Plan** – `sparc_orchestrator` or `boomerang`
   - Ask for a structured refactor plan focused on specific files/modules.

2. **Patterns & structure** – `architect`
   - Suggest better boundaries, layering, and patterns.

3. **Refactor & cleanup** – `refinement-optimization-mode` + `code`
   - Propose and then implement safe, incremental refactors.
   - Keep behavior stable but improve modularity and performance.

4. **Tests & docs** – `tdd` + `docs-writer`
   - Ensure tests still pass and docs reflect new structure.

---

## 4. Memory & context (Memory Bank)

If this repo uses a **Memory Bank** (for example, `memory-bank/productContext.md`, `activeContext.md`, `systemPatterns.md`, `decisionLog.md`, `progress.md`):

- Orchestrators (`sparc_orchestrator`, `boomerang`) and tutorial/ask agents should:
  - Read from these files to understand:
    - What the project is for.
    - Current focus and active work.
    - Established patterns and decisions.
  - Suggest short, timestamped updates to those files when:
    - A major decision is made.
    - A feature is completed.
    - A new pattern is introduced.

This keeps multi‑agent workflows grounded in consistent long‑term context, which multi‑agent references call out as critical for reliability and coordination.[web:179][web:193]

---

## 5. Usage tips for humans (and Copilot)

- **Start simple**  
  - For a brand‑new user, begin with: `tutorial` → `sparc_ask` → `sparc_orchestrator` before touching the specialist agents directly.

- **Think SPARC, not “one big prompt”**  
  - Break work into:
    - Specification
    - Pseudocode
    - Architecture
    - Refinement (code/tests/debug/security/optimization)
    - Completion (integration/docs/monitoring)

- **Keep tasks modular and safe**  
  - One main goal per agent call.
  - No hard‑coded secrets or env values.
  - Encourage files under ~500 lines where practical.

- **Ask for summaries**  
  - Each agent should end with:
    - What they did,
    - Where to find changes/artifacts,
    - Recommended next agent/task.

Following these patterns helps Copilot behave more like a **coordinated team** of specialists instead of a single all‑purpose chatbot.