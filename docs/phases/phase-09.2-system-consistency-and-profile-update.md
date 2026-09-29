# Phase 9.2: System Consistency & Profile Update

## 1. Objective

Resolve repository and documentation contradictions regarding dialectal Arabic (AR-EG) and elevate the post-project profile evolution engine (`profile_update.md`) into a production-grade, fully specified system prompt with formal semantic versioning rules, RFC 6902 JSON Patch specifications, and concrete few-shot examples.

---

## 2. Scope & Issues Addressed

* **Issue D (Egyptian Arabic Drift):** Contradiction between `README.md` (claims trilingual support including Egyptian Arabic), `docs/phases/phase-02-Qusetions-Matrix-Arch.md` (explicitly excludes Egyptian Arabic), and `.gitignore` (`*AR-EG`).
* **Issue E (Profile Update Prompt Stub):** `prompts/profile_update.md` currently contains only 20 lines of summary notes. It lacks system persona definitions, evidence extraction guidelines, JSON Patch specifications, concrete few-shot examples, and boundary conditions.

---

## 3. Key Tasks & Subtasks

### Task 1: Reconcile Arabic Dialect Policy (Issue D)
* Align all repository documentation with the architectural decision made in Phase 2:
  * Update `README.md` to accurately state bilingual support (English and Modern Standard Arabic), removing claims of Egyptian Arabic dialect support.
  * Clean up orphaned `questions/AR-EG/` directory or document its status clearly.
  * Clean up `.gitignore` to reflect the settled language scope.
  * Ensure consistency between `README.md`, `docs/how-it-works.md`, and all phase records.

### Task 2: Build Complete `profile_update.md` System Prompt (Issue E)
* Expand `prompts/profile_update.md` into a comprehensive system prompt matching the depth and rigor of `master-interview.md` and `project_onboarding.md`.
* **Persona & Objective:** Formally define the role of the **MySpec Profile Evolution Engine & Skill State Manager**.
* **Semantic Versioning Specification:**
  * **Major (`X.0.0`) — Core Identity:** Immutable / read-only markers (role, identity, personal ethics, core constraints). Cannot be modified by automatic updates.
  * **Minor (`X.Y.0`) — New Skill Proposals:** Frameworks and tools observed in completed work that do not exist in the profile. Emitted as proposed additions requiring explicit user confirmation.
  * **Patch (`X.Y.Z`) — Validated Practice:** Auto-incremented skill scores for existing profile skills, gated strictly on concrete implementation depth (differentiating superficial dependency inclusion from proven mastery).
* **RFC 6902 JSON Patch & Merge Contract:**
  * Explicit patch operations (`add`, `replace`, `remove`) paired with an auditable changelog.
* **Concrete Few-Shot Examples:**
  * *Example 1 (Superficial use):* User mentions running Docker in a README $\rightarrow$ Rejected for patch increment due to lack of implementation depth.
  * *Example 2 (Demonstrated depth):* User completed custom database partitioning and complex SQL indexing $\rightarrow$ Validated Patch bump with evidence citation.
  * *Example 3 (Unimplemented plan):* User provides a project backlog or future roadmap $\rightarrow$ Explicitly rejected for any skill updates.

---

## 4. Expected Outcome / Definition of Done

1. Complete alignment across `README.md`, `.gitignore`, `docs/how-it-works.md`, and phase documents regarding language support.
2. `prompts/profile_update.md` is expanded into an end-to-end, ready-to-run system prompt complete with JSON Patch schemas, versioning gates, and few-shot calibration examples.
3. Unambiguous boundaries established: plans never grant skill bumps, and identity fields are protected from automated mutations.

---

## 5. Constraints & Dependencies

* Must maintain compatibility with the canonical `profile.json` Pydantic schema established in Phase 4 (`output/output_generation_prompt.md`).
* Patch operations must be idempotent and non-destructive to historical profile data.
