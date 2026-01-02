---
trigger: always_on
---

<agentic_protocol_update version="2.1.0">
## CRITICAL OPERATIONAL PROTOCOL: MANDATORY FILE AUDIT

**Target Module:** Planning & Execution
**Enforcement Level:** STRICT / BLOCKING

To ensure codebase integrity and prevent regression, the following protocol is now ACTIVE and overrides default behaviors:

### 1. The "Blindness" Prohibition
The Agent is strictly prohibited from assuming the state of the codebase.
- **[REQUIRED]** `list_dir`: Must be called to map the active workspace.
- **[REQUIRED]** `view_file`: Must be called on ALL target files before generating an `implementation_plan.md`.

### 2. Evidence-Based Planning
The `implementation_plan.md` artifact must serve as proof of research.
- **Validation Rule:** Every proposed change must cite specific, existing line numbers found via `view_file`.
- **Failure Condition:** A plan without citations is considered a hallucination and must be rejected.

### 3. Execution Gate
The Agent may not enter EXECUTION mode until the User has explicitly approved the Evidence-Based Plan.
</agentic_protocol_update>