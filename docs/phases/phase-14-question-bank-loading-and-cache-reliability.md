# Phase 14: Question Bank Loading & Cache Reliability

> **Architectural Foundation & Source of Truth:**
> This phase strengthens the Markdown question-bank engine specified in [Phase 11.1](phase-11.1-refactor-question-bank-engine.md). The existing files under [`questions/EN`](../../questions/EN/) and [`questions/AR-MSA`](../../questions/AR-MSA/) remain the canonical question content. Parsed question records are validated before use or caching; this phase does not migrate the bank to another storage format.

---

## 1. Objective

Make question loading deterministic and fail clearly when the selected bank is missing, malformed, duplicated, or incomplete. Ensure a process never serves cached questions from a different bank directory merely because the language is the same.

Keep the local stdio server architecture and current Markdown authoring workflow. Preserve the existing public loader behavior where practical, with focused error types/messages that identify the selected file and question ID or source line when available.

---

## 2. Dependencies and Existing Contracts

* Phase 11.1 defines `MYSPEC_QUESTIONS_PATH`, the package-relative default, Markdown parsing, the 50 IDs (`Q01`–`Q50`), category ranges, and process caching.
* Phase 11.0 identifies the English and Arabic Markdown files as the canonical question content.
* The current implementation caches by language only and can overwrite duplicate IDs or omit incomplete blocks without rejecting the whole bank. This phase closes those reliability gaps.
* Use the repository's existing Python support and `unittest` conventions. Phase 12 is planned to establish the profile Pydantic contract, but it does not automatically validate question-bank records.
* Before implementation, confirm Pydantic is declared directly in `mcp-server/pyproject.toml` if `questions.py` imports it. Do not rely on an undeclared transitive dependency. Do not add runtime dependencies solely for JSON Schema validation.

---

## 3. Scope & Target Files

* **Modify**: `mcp-server/src/myspec_mcp_server/questions.py` (path-sensitive cache, strict parser behavior, full-bank validation, actionable loader errors)
* **Modify**: `mcp-server/tests/test_questions.py` (isolated path, parser, validation, cache, and parity failure coverage)
* **Modify**: `docs/phases/phase-11.1-refactor-question-bank-engine.md` (reconcile cache and validation requirements with the completed behavior)
* **Review/update if needed**: `docs/master_interview_architecture.md` and `mcp-server/README.md` (keep bank path, Markdown source-of-truth, cache lifetime, and failure behavior accurate)

Do not modify profile generation, profile persistence, interview completion rules, question wording, or unrelated MCP resources and tools.

---

## 4. Question Bank Contract

### 4.1 Source Format and Path Resolution

* Keep the seven category Markdown files per language as the only authored question source.
* Resolve the bank root through `MYSPEC_QUESTIONS_PATH` or the existing package-relative default, independently of the current working directory.
* Normalize the selected root to an absolute resolved path before using it for loading or cache identity.
* Report missing directories and files as explicit question-bank errors with the resolved path. Do not silently fall back to another root or language directory.

### 4.2 Parsed Question and Complete Bank Validation

Validate records when parsing and validate the assembled bank before returning it:

* Every question has a recognized ID, expected category, non-empty title and prompt, supported language, and the category's configured target modules.
* Every category contains exactly the IDs in its configured inclusive range, in the expected order.
* The complete language bank contains every ID from `Q01` through `Q50` exactly once; reject duplicate, missing, unexpected, or out-of-range IDs.
* Reject malformed question blocks instead of dropping them. A block with a heading but no localized prompt, or a prompt without a valid heading, is an error.
* English and Arabic banks each contain the complete ID set. Add a parity check in tests (or an explicit validation entry point) that ensures both language banks expose the same IDs.
* Keep category, file, and target-module metadata in one authoritative mapping. Do not duplicate those rules in the model, parser, and tests as independent constants.

If Pydantic is used, define a question record model and a bank-level model/validator for cross-record rules. Use strict field validation where appropriate and reject extra fields if the parsed record contract is intended to be closed. A per-question model alone cannot detect duplicates or missing IDs; those checks belong at the assembled-bank boundary.

### 4.3 Cache Contract

Keep a small in-process cache for the stable, local bank. Key it by both resolved bank root and normalized language (conceptually `(resolved_root, language)`).

* Resolve the root on each public load request before checking the cache, so changing `MYSPEC_QUESTIONS_PATH` to another directory selects another cache entry.
* Cache only a complete, successfully validated bank. Never cache partial or invalid data.
* Keep cache lifetime limited to the server process; do not add TTLs, file watchers, or general invalidation infrastructure.
* Do not promise hot reload for edits made in place to the same bank directory during a running process. Restarting the local server is the documented refresh mechanism unless a demonstrated requirement justifies a later change.
* Avoid mutating shared cached records from consumer code. Return read-only structures or defensive copies if needed to prevent one caller from corrupting subsequent results.

This phase chooses path-sensitive caching because the server process benefits from loading the small, stable bank once, while the cache key must distinguish configured bank roots. Removing the cache may be reconsidered if measurements or an explicit live-edit requirement show a benefit.

### 4.4 Error Reporting

Expose a common question-bank exception base so callers can handle loading failures consistently. Distinguish missing files, invalid UTF-8/Markdown structure, invalid question fields, duplicate IDs, and incomplete banks where doing so keeps errors clearer.

Error messages should name the resolved file and include the question ID or source line where available. Preserve the underlying exception as the cause. Do not include question content unnecessarily in MCP errors.

---

## 5. Implementation Stages

### Stage 1 — Define and Validate the Bank Contract

1. Centralize the expected question IDs, category ranges, filenames, language labels, and target-module metadata.
2. Define record-level validation and bank-level validation for the Markdown parser output.
3. Make malformed or incomplete blocks explicit errors and retain line context during parsing where practical.
4. Define the common loader error contract and ensure missing/unreadable roots and files are actionable.
5. Keep Markdown as the canonical authored format; do not add JSON bank files or hand-maintained duplicate schemas.

#### Stage 1 Acceptance Criteria

* The contract covers required fields, supported languages, category membership, question ordering, and exact bank completeness.
* Duplicate, missing, unexpected, and malformed question records cannot be silently accepted or dropped.
* English and Arabic retain the same stable `Q01`–`Q50` identity set.

### Stage 2 — Implement Path-Sensitive Cache and Loading Behavior

1. Resolve `MYSPEC_QUESTIONS_PATH` or the package-relative root to an absolute path before each cache lookup.
2. Key validated banks by resolved root and normalized language.
3. Parse and validate the entire bank before inserting it into the cache; leave the cache unchanged on any load or validation failure.
4. Ensure `load_category_questions`, `load_all_questions`, and `get_question_pair` surface loader failures rather than returning partial results.
5. Prevent consumers from mutating cached question records, using immutable data or defensive copies consistent with the existing API.
6. Keep startup and runtime local-only; add no network access, database, file watcher, or external cache service.

#### Stage 2 Acceptance Criteria

* Switching between two configured bank roots in one process returns questions from the selected root for both languages.
* Repeated requests for the same resolved root and language reuse a complete validated bank.
* A failed load never creates a cached partial bank, and cache identity does not depend on the current working directory.
* Question pair behavior remains exactly two stable IDs per interview turn for valid banks.

### Stage 3 — Add Failure-Path Tests and Align Documentation

1. Add temporary-directory fixtures for valid and intentionally damaged English and Arabic Markdown banks.
2. Test malformed headings/prompts, missing files, invalid encoding, duplicate IDs, missing IDs, unexpected IDs, wrong category ranges, empty required fields, and language mismatch.
3. Test cache separation when `MYSPEC_QUESTIONS_PATH` changes between roots in a single process, and verify invalid banks are not cached.
4. Test English/Arabic ID parity and first/last question-pair boundaries.
5. Test that consumers cannot mutate cached data in a way that changes later results.
6. Update Phase 11.1 and relevant setup/architecture docs to describe the final source format, path resolution, process cache, validation, and restart-to-refresh behavior.

#### Stage 3 Acceptance Criteria

* Tests cover both successful loading and each required failure mode through public loader entry points.
* Cache tests fail if the cache is keyed only by language or if invalid results are cached.
* Existing interview question ordering and pair behavior remain covered.
* Documentation consistently describes Markdown as the canonical bank format and does not promise silent recovery or hot reload.

---

## 6. Explicitly Out of Scope

* Migrating question content from Markdown to JSON or changing question wording.
* JSONPath or another query-language dependency for a flat, fixed question set.
* Runtime JSON Schema validation or a separately maintained schema that duplicates the model.
* No-cache-by-default or live hot reload during a server process; the process cache is retained with path-and-language identity.
* Automatic fallback to another root, another language, or an older/partial bank.
* Hypothesis, pytest, or other new test dependencies unless a later measured need justifies them.
* General-purpose cache TTLs, file watchers, cache services, remote storage, or databases.
* Profile schema, interview answer validation, profile mapping, persistence, or unrelated MCP behavior.

---

## 7. Future Work — Nearest Follow-Ups

These items are deliberately deferred so Phase 14 can close the current loading and cache reliability issue without expanding into content migration or broader interview redesign. After Phase 14 is implemented and its tests pass, review these in order and create a separate phase only when the need is confirmed:

1. **Question-bank format decision:** Assess whether Markdown remains the best canonical authoring format or whether a future JSON migration would materially improve editing, tooling, or distribution. If a migration is chosen, define a one-time conversion, review every translated question, preserve stable IDs, and update the standalone prompt/docs together. Do not maintain two editable sources of truth.
2. **Live reload decision:** Measure startup/load behavior and gather an explicit need for same-process bank edits before designing cache invalidation. If required, specify a simple safe refresh boundary and tests rather than adding a watcher preemptively.
3. **Translation quality workflow:** Consider a separate content-quality review for English/Arabic semantic parity. ID parity verifies structure, not translation accuracy; that requires human review or a dedicated editorial workflow.
4. **Remaining MCP reliability issues:** Once the question bank is stable, prioritize the still-open high-impact server issues from the project review, beginning with duplicated profile mapping and uncovered interview tool failure cases, while keeping each phase independently scoped.

No future item above is required to complete Phase 14.

---

## 8. Definition of Done

* [ ] Markdown remains the sole authored source for English and Arabic questions.
* [ ] Every selected bank is fully parsed and validated before any caller receives or caches it.
* [ ] Missing, malformed, duplicate, unexpected, and incomplete question sets produce actionable errors.
* [ ] The process cache is keyed by resolved bank root and normalized language and stores only validated banks.
* [ ] Changing the configured root cannot return entries from a previous root; invalid loads cannot poison the cache.
* [ ] Existing question ordering, language behavior, and interview pair boundaries remain intact.
* [ ] Failure-path tests and documentation updates are complete.
* [ ] No unrelated application features or infrastructure are introduced.
