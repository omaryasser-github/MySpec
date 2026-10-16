# Phase 13: Profile Contract, Validation & Data Integrity

> **Architectural Foundation & Source of Truth:**  
> This phase extends the profile assembly and MCP interview workflow defined in [Phase 11.2](phase-11.2-refactor-profile-assembly-and-persistence.md), [Phase 11.3](phase-11.3-refactor-mcp-tool-surface.md), [Phase 11.4](phase-11.4-refactor-prompt-decoupling-and-e2e.md), and [Phase 12](phase-12-question-bank-loading-and-cache-reliability.md). The canonical question bank contracts, IDs, and category mappings validated in Phase 12 are the direct foundation for answer validation and profile assembly in this phase. The canonical profile contract in [`output/output_generation_prompt.md`](../../output/output_generation_prompt.md) is reconciled with the executable model here.

---

## 1. Objective

Establish one authoritative, versioned profile contract and enforce it across answer intake, profile assembly, persistence, and profile reads. Invalid or incomplete data must not be silently accepted as a valid canonical profile, and validation failures must return useful MCP tool errors that the host can act on.

The interview host supplies structured answers to `finalize_interview`; the MCP server deterministically validates and assembles those answers. The server does not call an LLM or generate profile content itself.

---

## 2. Dependencies

Complete and review the contracts introduced by Phase 12 and Phases 11.1 through 11.4 before implementation. In particular:

* Phase 12 defines the centralized canonical question IDs (`Q01`–`Q50`), category mappings, and validated bank cache.
* Phase 11.2 defines `build_profile` and profile persistence.
* Phase 11.3 defines the interview tool inputs, progression, and completion behavior.
* Phase 11.4 defines the prompt and end-to-end workflow boundaries.

Resolve any inconsistencies between those phase specifications and `output/output_generation_prompt.md` as part of Stage 1. This phase must not introduce a second profile contract.

---

## 3. Scope & Target Files

* **Modify**: `mcp-server/src/myspec_mcp_server/profile.py` (canonical model, validation helpers, module dict key conventions, `extract_skills` alignment, and validation gates)
* **Modify**: `mcp-server/src/myspec_mcp_server/server.py` (tool signatures defaulting `language: str | None = None`, `finalize_interview(output_preference=...)`, answer validation, and actionable MCP tool failures)
* **Modify**: `mcp-server/pyproject.toml` (declare the selected Pydantic v2 dependency if it is not already available through the supported MCP SDK dependency contract)
* **Modify**: `output/output_generation_prompt.md` (align the documented profile schema and generation instructions with the canonical model)
* **Modify**: `docs/phases/phase-11.2-refactor-profile-assembly-and-persistence.md` and related phase documentation as needed to remove conflicting profile field and persistence requirements
* **Modify**: `mcp-server/tests/test_profile.py`, `mcp-server/tests/test_server.py`, and relevant question-bank tests (contract, MCP error assertions, and failure-path coverage)

Do not modify question text or implement unrelated question caching or prompt-decoupling work in this phase.

---

## 4. Implementation Stages

### Stage 1 — Define the Profile Contract

Create one authoritative Pydantic v2 model for the canonical profile. Use strict validation for metadata and answer values where coercion could conceal malformed input, and reject unexpected top-level fields.

#### 4.1 Resolve the Canonical Fields

Reconcile the model with the existing profile contract and specify each field's requiredness, JSON type, constraints, and serialization behavior:

* `schema_version`: positive integer with an explicit supported version.
* `completed_at`: timezone-aware timestamp serialized as ISO 8601.
* `status`: supported lifecycle enum, including the defined complete and partial states; retain `stale` only if existing profile requirements still use it.
* `completion_rate`: numeric value from 0.0 through 1.0 with a defined calculation over the canonical 50 question IDs.
* `output_preference`: enum of `bilingual`, `english_only`, `arabic_only`, or `none`. Add `output_preference: str = "english_only"` to `finalize_interview` tool parameters and propagate to `build_profile`.
* `skipped_fields`: unique question IDs with explicitly defined meanings for declined, unknown, not-applicable, unanswered, and unresolved clarification states.
* `language`: normalize tool parameters across `start_interview`, `advance_interview`, and `finalize_interview` to default to `language: str | None = None` so that an omitted language explicitly evaluates `get_language()` / `MYSPEC_LANG`. Decide whether `language` is canonical persisted profile metadata or session metadata.
* `updated_at`: decide whether it is part of the canonical contract or whether `completed_at` alone records profile completion/update time. Do not keep both fields with unclear or conflicting semantics.
* Seven dynamic modules: `identity`, `current_skills`, `learning_in_progress`, `limitations`, `communication_prefs`, `work_context`, and `growth_goals`. Clarify module dict key conventions: store question IDs (`Q01`..`Q50`) deterministically as keys in the dynamic module dicts, and align `extract_skills()` in `profile.py` so that tools in `work_context` are extracted from question values/text rather than requiring dictionary keys to match substring `"tool"`.

Define cross-field invariants for status, completion rate, and dispositions. A fully resolved interview may be complete; a permitted partial interview must remain explicitly partial, with unresolved or declined IDs represented consistently. An unprovided answer must not be silently counted as resolved.

#### 4.2 Generate the JSON Schema from the Model

* Generate the Draft 2020-12 JSON Schema from the Pydantic model. Do not maintain a second hand-authored executable schema.
* Keep `additionalProperties: false` at the canonical profile object's top level. Model the seven modules deliberately so their dynamic keys and allowed JSON values remain valid without opening unrelated top-level properties.
* Include schema/version metadata in the schema artifact and keep the profile's `schema_version` in the profile data. `$schema` identifies the JSON Schema dialect; it is not a profile data field unless the profile contract explicitly adopts it.
* Align `output/output_generation_prompt.md` and affected phase documents with the model's exact fields, enums, defaults, and examples.

#### 4.3 Stage 1 Acceptance Criteria

* One model is the source of truth for executable validation and generated JSON Schema.
* The documented profile contract matches the generated schema and serialized model.
* Timestamp, language, output preference, status, and partial-completion semantics are unambiguous.
* The seven modules accept only their documented dynamic JSON content; unexpected top-level fields are rejected.

### Stage 2 — Implement Validation and Error Handling

Apply validation at each data boundary before data can be treated as canonical or persisted.

#### 4.4 Validate Interview Answers

* Validate every supplied question ID against the canonical `Q01`–`Q50` set.
* Validate answer values as strings or explicitly supported disposition values; reject nulls, wrong types, blank values where not allowed, and unsupported disposition markers.
* Check that the answers for the current pair are present or explicitly resolved before `advance_interview` advances.
* Define finalization rules from the existing complete/partial interview contract. Reject missing or unresolved IDs when complete finalization is requested; allow partial finalization only when represented explicitly and consistently.
* Ensure completion rate and `skipped_fields` derive from the validated canonical question state, not from counts of values copied into profile modules.

#### 4.5 Validate Assembly, Reads, and Writes

* Validate the result of `build_profile` against the canonical model before it is returned or passed to persistence.
* Validate again at the `save_profile` boundary so callers cannot bypass the persistence guard.
* Validate loaded JSON profiles against the supported schema version and classify invalid or unsupported data through the server's existing graceful profile-status behavior. Preserve Markdown compatibility according to its existing documented contract; do not pretend unstructured Markdown has passed canonical JSON validation.
* Do not write a profile if answer validation, model validation, serialization, or other pre-write validation fails.

#### 4.6 Return Actionable MCP Tool Errors

* Use the installed Python MCP SDK's supported tool-error mechanism so expected validation failures reach the host as a tool result with `isError: true` and readable text.
* Update existing tests in `test_server.py` that previously asserted dictionary keys `{"error": ...}` to assert against SDK `isError: true` tool results.
* Include a concise failure reason, the relevant field or question ID, the expected value/shape, and a correction hint when useful. Avoid returning raw tracebacks or sensitive profile contents.
* Do not return an ordinary successful dictionary containing an `error` key for a failed tool call.
* If a tool advertises an output schema, keep successful `structuredContent` within that schema. Do not attach invalid profile data as structured output on an error result.
* Keep the server's local-only stdio architecture and existing profile privacy guarantees.

#### 4.7 Stage 2 Acceptance Criteria

* Unknown IDs, invalid values, unresolved pair answers, and inconsistent completion state are rejected before progression or finalization.
* `build_profile` and `save_profile` both enforce the same canonical model.
* Invalid profiles are never written, and validation failures produce SDK-supported MCP tool errors.
* Invalid JSON profiles are reported gracefully on read, and existing Markdown profiles retain their documented behavior.

### Stage 3 — Add Comprehensive Tests

Add unit and MCP-surface tests for successful validation, every contract boundary, and expected failure behavior. Tests must verify behavior, not merely call the functions.

#### 4.8 Required Test Coverage

**Profile model and generated schema**

1. Valid complete and valid partial profiles serialize and validate successfully.
2. Missing required top-level fields fail with actionable validation details.
3. Unexpected top-level fields fail; dynamic module entries remain accepted only in the documented shape.
4. Incorrect types and invalid enum values fail without implicit coercion where strictness is required.
5. Invalid timezone-naive timestamps and out-of-range completion rates fail.
6. Cross-field violations fail, including inconsistent status/completion rate and inconsistent skipped/disposition data.
7. Generated JSON Schema reflects the model's required fields, enums, constraints, and closed top-level object.

**Answer and interview tools**

8. Unknown question IDs, unsupported disposition markers, null/wrong-type answers, and disallowed blank answers are rejected.
9. `advance_interview` does not advance when either current question lacks an answer or explicit disposition.
10. Finalization rejects an invalid complete interview and handles an explicitly permitted partial interview according to the contract.
11. MCP clients observe validation failures as `isError: true`, with useful text and no invalid `structuredContent`.

**Persistence and profile reads**

12. A valid profile is saved and can be loaded as canonical JSON.
13. Invalid data passed to `save_profile` is rejected before any destination file is written or replaced.
14. A simulated write failure is reported as a tool failure; tests assert that no invalid profile is reported as successfully saved and that pre-existing valid data is not falsely reported as updated.
15. Malformed or unsupported-version JSON is classified gracefully on read; Markdown profile behavior remains compatible.

#### 4.9 Stage 3 Acceptance Criteria

* All required success and failure cases above have automated coverage.
* Tests prove that validation failures do not persist invalid data.
* Tests verify MCP error semantics through the client/server surface, not only by inspecting an exception.
* The full MCP server test suite passes after implementation.

---

## 5. Explicitly Out of Scope

* Server-side LLM calls, profile generation, or retrying generation. The host supplies structured answers; MySpec validates and assembles them.
* JSON repair, regular-expression cleanup of model output, or permissive normalization of invalid data.
* Backup rotation, `.bak` recovery, restore procedures, or other advanced backup/recovery mechanisms.
* Changes to the stdio-only, local-first deployment boundary, or introduction of network services, remote persistence, telemetry, or a database.
* Question wording changes or unrelated question-bank cache behavior.

---

## 6. Definition of Done

* [ ] The canonical profile model is strict, versioned, and generates the JSON Schema used by the project.
* [ ] The output-generation prompt and dependent phase documentation match the canonical model.
* [ ] Answer intake, profile assembly, profile reads, and persistence enforce the specified validation boundaries.
* [ ] Validation errors use the MCP SDK-supported tool-error path and explain how to correct the input.
* [ ] No invalid profile is saved or presented as successfully finalized.
* [ ] All required tests pass, including MCP-level error and write-failure tests.
* [ ] The local-only stdio architecture and documented Markdown compatibility remain intact.
