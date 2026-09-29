# Phase 9.1: Core Architecture & Contract Fixes

## 1. Objective

Establish robust foundational data contracts across the MySpec system by:
1. Solving the standalone prompt delivery issue so the interview prompt executes seamlessly in web chat LLM environments without external file dependencies.
2. Transforming existing category topic outlines into a canonical 50-question bank with stable, immutable IDs (`Q01`–`Q50`).
3. Harmonizing the format and discovery contract (`profile.json` vs `profile.md`) between profile generation, documentation, and the local MCP server.

---

## 2. Scope & Issues Addressed

* **Issue A (Standalone Prompt Delivery):** In web interfaces (ChatGPT, Claude, Gemini Web), LLMs cannot access local disk paths (`/questions/EN/...`). The master interview prompt must provide a self-contained question payload or bundled distribution format.
* **Issue B (Canonical Question Matrix):** Current files in `questions/` contain topic outlines and bullet points rather than formulated questions. This creates non-deterministic questioning and conflicts with the strict 50-question / 25-turn state machine contract.
* **Issue C (Profile Format & Path Contract):** Output generation produces canonical `profile.json`, whereas the local MCP server defaults to searching exclusively for `~/.myspec/profile.md`, causing missing-profile false alarms.

---

## 3. Key Tasks & Subtasks

### Task 1: Formulate the Canonical 50-Question Bank (Issue B)
* Convert the 50 topic headings across the 7 categories into explicit, formulated interview questions with immutable IDs:
  * **Category 1: Identity & Work:** `Q01` through `Q10`
  * **Category 2: Communication Style:** `Q11` through `Q18`
  * **Category 3: Knowledge & Skills:** `Q19` through `Q25`
  * **Category 4: Tools & Workflows:** `Q26` through `Q32`
  * **Category 5: Decision-Making:** `Q33` through `Q38`
  * **Category 6: Goals & Priorities:** `Q39` through `Q44`
  * **Category 7: Personal Context:** `Q45` through `Q50`
* Format each entry with:
  * The exact question text to be presented by the AI.
  * Contextual prompts and sub-bullets preserved as guidance/rubric for evaluation.
* Synchronize English and Modern Standard Arabic (MSA) matrices.

### Task 2: Implement Standalone Prompt Strategy (Issue A)
* Design a distribution mechanism or inlined question bank format for `master-interview.md`:
  * Embed the canonical 50-question bank directly into `<QUESTIONS_BANK>` within the prompt, or provide a generated distribution bundle (e.g., `dist/master-interview-standalone.md`).
  * Ensure a user can copy a single prompt file directly into any web LLM without requiring filesystem access.
  * Retain modular category files in `questions/` for maintainability and granular referencing.

### Task 3: Unify Profile Contract & MCP Path Fallback (Issue C)
* Update `output_generation_prompt.md` to clarify the artifact delivery contract:
  * Canonical machine profile: `profile.json` (SSOT).
  * Human-readable profile: `profile.md`.
* Update `get_profile_path` in `mcp-server/src/myspec_mcp_server/profile.py` to support dual-format resolution:
  1. Respect `MYSPEC_PROFILE_PATH` override if provided.
  2. Fall back to `~/.myspec/profile.md` if it exists.
  3. Fall back to `~/.myspec/profile.json` if `profile.md` is absent.
* Update documentation in `README.md` and `mcp-server/README.md` to reflect dual format support.

---

## 4. Expected Outcome / Definition of Done

1. All 50 interview questions have stable, explicit identifiers (`Q01` to `Q50`) and full question sentences.
2. The master interview prompt can be pasted into any standard web chat interface and execute from start to finish without asking the user for local question files.
3. The MCP server automatically discovers and loads either `profile.md` or `profile.json` from `~/.myspec/` without manual configuration.
4. All existing and updated unit tests pass.

---

## 5. Constraints & Dependencies

* Must preserve the 2-question per turn (25 turns total) pacing and 7-category progression.
* Must maintain bilingual parity (English and Modern Standard Arabic).
* Stdio-only, read-only guarantees of the MCP server must remain intact.
