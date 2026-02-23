# Copilot Training Agent — Compliance, Architecture & Roo Code Memory Bank

## Purpose

This agent trains GitHub Copilot to generate consistent, production-ready,
compliance-aware code by learning from this repository’s codebase,
documentation, and Roo Code memory-bank.

Copilot MUST analyze existing code, approved examples, and memory-bank
documentation to infer preferred patterns, prohibited practices, and
regulatory constraints, and MUST carry these forward into all future code
generation, refactoring, and suggestions.

---

## Authoritative Knowledge Sources

Copilot MUST treat the following as authoritative, in this priority order:

1. Roo Code memory-bank (`memory-bank/`)
2. Explicit compliance documentation
3. Existing compliant production code
4. Local file context
5. General best practices

Copilot MUST NOT violate higher-priority sources to satisfy lower-priority ones.

---

## Roo Code Memory Bank Integration

This repository uses Roo Code’s memory-bank as the persistent,
authoritative knowledge base.

Copilot MUST:
- Read and respect all files under `roo-code/memory-bank/`
- Apply memory-bank rules consistently across the entire codebase
- Treat memory-bank guidance as higher priority than inferred patterns

Copilot MUST NOT:
- Contradict memory-bank guidance
- Reinterpret compliance rules defined in memory-bank
- Introduce patterns explicitly marked as disallowed

### Memory Bank File Semantics

Copilot SHOULD assume the following conventions:

- `architecture.md`  
  Canonical system structure, layering rules, module boundaries

- `compliance.md`  
  Regulatory interpretations, audit constraints, mandatory controls

- `security.md`  
  Threat models, approved cryptography, authentication and authorization rules

- `patterns.md`  
  Approved reusable implementation patterns

- `anti-patterns.md`  
  Explicitly forbidden practices that MUST NOT be reintroduced

These files define long-term institutional knowledge and persist across
all features and refactors.

---

## Compliance & Regulatory Requirements

Compliance rules are **hard constraints**.

Copilot MUST:
- Enforce all compliance requirements defined in memory-bank and documentation
- Prefer explicit, auditable logic over implicit or clever implementations
- Preserve traceability of data flow and control flow

If a request violates compliance:
- Copilot MUST refuse to implement it
- Copilot MUST explain why it is non-compliant
- Copilot MUST suggest a compliant alternative

---

## Architecture & Framework Awareness

Copilot MUST:
- Follow the established architecture and layering
- Use framework-native abstractions consistently
- Respect module and package boundaries
- Maintain dependency direction rules

Copilot MUST NOT:
- Introduce new frameworks or libraries without precedent
- Bypass existing abstractions or service layers
- Mix concerns across layers

---

## Coding Patterns & Style Inference

Copilot SHOULD learn by observation from approved code and retain:

- Naming conventions
- File and folder organization
- Error handling strategies
- Dependency injection patterns
- Logging and observability practices

When generating new code:
- Match surrounding style exactly
- Prefer consistency over novelty
- Optimize for readability and maintainability

---

## Do / Don’t Rules

### DO
- Validate all external inputs
- Handle errors explicitly and deterministically
- Write testable, deterministic logic
- Prefer immutability where practical
- Document non-obvious decisions

### DON’T
- Hardcode secrets, credentials, or environment values
- Suppress or ignore errors
- Use unsafe language features or APIs
- Introduce silent breaking changes
- Reuse patterns that conflict with memory-bank rules

---

## Security & Privacy Expectations

Copilot MUST:
- Assume zero trust for all external inputs
- Follow least-privilege principles
- Avoid logging sensitive or regulated data
- Prefer secure defaults over permissive behavior

Copilot MUST flag:
- Injection vulnerabilities
- Insecure deserialization
- Weak or deprecated cryptography
- Unauthorized data access patterns

---

## Learning From Examples

Code explicitly marked as:
- `// compliant`
- `// approved pattern`
- `// reference implementation`
- `// roo:approved`

MUST be treated as canonical examples.

Code marked as:
- `// anti-pattern`
- `// do not use`
- `// legacy`
- `// roo:forbidden`

MUST NOT be reused or reintroduced.

---

## Change & Refactor Behavior

When modifying existing code, Copilot MUST:
- Preserve compliance guarantees
- Maintain backward compatibility unless instructed otherwise
- Avoid stylistic rewrites unless requested
- Explain any structural or behavioral changes

---

## Output Quality Requirements

All generated code MUST:
- Compile or run in the existing environment
- Align with architecture, compliance, and security rules
- Be production-ready by default
- Favor clarity over cleverness

When uncertain:
- Ask for clarification
- Or choose the safest, most compliant option

---

## Priority Order (Highest → Lowest)

1. Compliance & Security
2. Roo Code Memory-Bank Rules
3. Architecture & Framework Constraints
4. Consistency With Existing Code
5. Performance Optimizations
6. Convenience or Brevity

Copilot MUST NEVER violate a higher-priority rule to satisfy a lower-priority one.
