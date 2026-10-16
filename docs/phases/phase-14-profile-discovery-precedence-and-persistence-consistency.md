# Phase 14: Profile Discovery, Precedence & Persistence Consistency

> **Architectural Foundation & Source of Truth:**
> This phase resolves the profile location and persistence contract built on by [Phase 11.2](phase-11.2-refactor-profile-assembly-and-persistence.md) and [Phase 13](phase-13-profile-validation-and-contracts.md). Phase 13's Pydantic model is the authoritative profile data contract. This phase defines which canonical file is read and written, how local configuration selects that file, and how a legacy Markdown profile is migrated once without runtime dual-format reads.

---

## 1. Objective

Make `profile.json` the single canonical profile source for every MCP resource, tool, prompt, and profile update. A successful save must update the same file that the next profile read uses, regardless of the process working directory or which supported configuration source selected the profile path.

Define deterministic path precedence, provide a deliberate one-time migration path for existing `profile.md` data, validate profiles with the Phase 13 Pydantic model, and write canonical JSON safely using an atomic same-directory replacement.

The MCP server remains a single-user, local-only stdio process. This phase adds no database, remote service, telemetry, or general-purpose storage framework.

---

## 2. Dependencies

Complete Phase 13 before implementing this phase. Phase 13 establishes the canonical model, supported schema version, profile validation rules, and invalid-profile behavior that migration and persistence must use.

Review and reconcile the existing contracts in:

* [Phase 11.2](phase-11.2-refactor-profile-assembly-and-persistence.md), which currently says that a `.md` profile path writes to a sibling `profile.json`.
* [Phase 13](phase-13-profile-validation-and-contracts.md), which currently preserves Markdown compatibility on reads.
* [`output/output_generation_prompt.md`](../../output/output_generation_prompt.md), which defines canonical JSON and Markdown companion artifacts.
* [`mcp-server/README.md`](../../mcp-server/README.md), [`README.md`](../../README.md), and [`docs/how-it-works.md`](../how-it-works.md), which currently describe Markdown-first or dual-format discovery.
* [Phase 8](phase-08-local-mcp-server.md), [Phase 9.1](phase-09.1-core-architecture-and-contract-fixes.md), and [Phase 10](phase-10-documentation-and-visual-architecture.md), which contain older default-path and fallback rules.

Update those contracts as part of implementation so none continue to promise Markdown as a runtime profile source.

---

## 3. Canonical Discovery Contract

### 3.1 Canonical File

* The canonical profile is JSON and must validate against the Phase 13 Pydantic model before it is returned or persisted.
* The default canonical path is `~/.myspec/profile.json`.
* `profile.md` may remain as a human-readable generated companion or as a preserved legacy migration source. The MCP server does not load it as profile context after this phase.
* Do not write both formats as independently authoritative profiles. If a Markdown companion is emitted, it is a derived export from canonical JSON and is never read back by MCP resources, tools, or prompts.

### 3.2 Path-Resolution Precedence

Resolve one exact canonical JSON path in this order:

1. **CLI:** An explicitly supplied `--profile` argument.
2. **Environment:** `MYSPEC_PROFILE_PATH`.
3. **MySpec config file:** `profile_path` in `~/.myspec/config.json`.
4. **Default:** `~/.myspec/profile.json`.

The MySpec config file is separate from the MCP host's server-launch configuration. Its only responsibility in this phase is the MySpec profile path; do not add a broad settings framework.

For every selected path:

* Expand `~` and environment-variable references, then resolve it to an absolute path.
* Require the resolved canonical profile path to use the `.json` suffix. A `.md` path is a legacy source and must be passed to the migration flow, not silently treated as a writable canonical destination.
* Once a higher-priority source provides a path, an invalid value or unreadable selected file is an actionable configuration/profile error. Do not silently fall through to a lower-priority source based on file existence or parse success.
* If a valid selected path does not exist, report the canonical profile as missing at that path. Do not probe neighboring Markdown or JSON files.
* Keep the default and config-file paths independent of the current working directory.

### 3.3 One-Time Markdown Migration

Provide a deliberate, user-invoked migration operation. Starting the MCP server must not silently migrate, archive, delete, or rewrite files.

The migration operation must:

1. Select the destination using the same CLI → `MYSPEC_PROFILE_PATH` → config file → default precedence, unless the user explicitly supplies a migration destination.
2. Select the legacy Markdown source explicitly, defaulting only when the migration operation documents a known legacy location such as `~/.myspec/profile.md`.
3. Refuse to overwrite an existing canonical JSON profile. Migration is not a profile merge or update operation.
4. Parse the supported legacy Markdown shape with a deterministic converter. Do not use a generic Markdown-to-dictionary conversion as proof that content maps correctly to profile semantics.
5. Validate the complete converted profile with the Phase 13 Pydantic model before writing.
6. Preserve the original Markdown file. Create a recoverable archive copy as part of a successful migration; never delete or move the source automatically.
7. Persist the validated JSON atomically. Report the source, destination, and outcome without exposing profile contents.
8. On parse, validation, archive, or write failure, report an actionable error and leave the original source unchanged. Do not report success or produce a partially written canonical profile.

After migration, ordinary server execution reads only the resolved JSON file. If a legacy Markdown file remains and the canonical JSON is missing, report that migration is required; do not read Markdown as a fallback. A repeat migration must not overwrite an existing JSON profile.

---

## 4. Scope & Target Files

* **Modify**: `mcp-server/src/myspec_mcp_server/profile.py` (path resolution, JSON-only profile reads, migration conversion, validation, and canonical persistence)
* **Modify**: `mcp-server/src/myspec_mcp_server/server.py` and/or a focused CLI module (profile path option and explicit migration entry point, while preserving stdio server launch behavior)
* **Modify**: `mcp-server/pyproject.toml` (CLI entry points or config dependencies only if the selected implementation requires them; reuse Phase 13's Pydantic dependency)
* **Modify**: `mcp-server/README.md`, `README.md`, and `docs/how-it-works.md` (canonical location, precedence, migration instructions, and host configuration)
* **Modify**: `output/output_generation_prompt.md` (JSON as canonical artifact; Markdown is a derived companion, never a runtime source)
* **Modify**: `docs/phases/phase-08-local-mcp-server.md`, `phase-09.1-core-architecture-and-contract-fixes.md`, `phase-10-documentation-and-visual-architecture.md`, `phase-11.2-refactor-profile-assembly-and-persistence.md`, and `phase-13-profile-validation-and-contracts.md` (remove obsolete discovery and fallback requirements)
* **Modify**: `mcp-server/tests/test_profile.py`, `mcp-server/tests/test_server.py`, and focused migration/configuration tests (path precedence, canonical read-after-write, and migration behavior)

Do not change the profile schema established by Phase 13, question-bank behavior, interview answer rules, or unrelated MCP resources and tools.

---

## 5. Implementation Stages

### Stage 1 — Finalize the Path and Migration Contract

1. Specify the CLI option name and behavior, retaining the existing `myspec-mcp-server` stdio entry point when no migration command is requested.
2. Define `~/.myspec/config.json` as a small MySpec-owned configuration file with a `profile_path` string; document missing, malformed, and unsupported config behavior.
3. Define path normalization and validation once, and ensure every profile consumer calls the same resolver.
4. Define the supported legacy Markdown shape and deterministic field mapping. Record which content cannot be migrated automatically and how the migration operation reports it.
5. Confirm that `.md` input is used only by the explicit migration operation and that no profile consumer performs fallback reads.
6. Align all affected documentation listed in Scope & Target Files with the finalized behavior.

#### Stage 1 Acceptance Criteria

* CLI, environment, config, and default sources have the documented precedence.
* The config file is clearly identified as MySpec-owned and distinct from MCP host configuration.
* All selected paths resolve independently of the current working directory and identify a `.json` canonical profile.
* Markdown conversion scope, source preservation, and failure behavior are explicit.
* No documentation claims that the MCP server reads Markdown as a fallback.

### Stage 2 — Implement JSON-Only Discovery and Safe Persistence

1. Implement the shared path resolver with the defined precedence. Invalid explicit higher-priority settings must return an actionable error rather than silently selecting a lower-priority path.
2. Make every MCP resource, tool, prompt, and profile update read the resolved canonical JSON file only.
3. Keep missing, unreadable, malformed, and unsupported-version profile states explicit and compatible with the existing graceful MCP responses.
4. Validate profile data with the Phase 13 Pydantic model before serialization and before every save.
5. Write JSON to a temporary file in the destination directory, flush and `fsync` the file, then replace the destination with `os.replace`. Clean up the temporary file on failure and preserve any existing valid destination until replacement succeeds.
6. Implement the explicit migration operation: refuse destination overwrite, parse only supported Markdown, validate before persistence, preserve the source, archive it, and write canonical JSON atomically. Return success only after the JSON can be read and validated at the selected path.
7. Do not introduce SQLite, a storage abstraction framework, a database, remote persistence, or general backup/recovery behavior.

#### Stage 2 Acceptance Criteria

* A profile saved by `finalize_interview` is the exact profile read by subsequent resources, tools, and prompts.
* No ordinary profile read probes or loads `profile.md` or a neighboring file.
* Explicit path selection and config errors do not silently fall back to another source.
* Migration is user-invoked, repeat-safe, does not overwrite JSON, and leaves the Markdown source intact on both success and failure.
* Invalid profile data is never persisted; interrupted or failed writes do not replace the prior valid JSON profile with partial data.

### Stage 3 — Add Tests and Verify Documentation

Add unit, CLI/config, migration, and MCP-surface tests. The tests must demonstrate the contract through public entry points and profile consumers.

#### Required Test Coverage

1. CLI path overrides environment, environment overrides config, config overrides the default, and default resolution does not depend on the working directory.
2. Tilde/environment expansion produces the expected absolute `.json` path.
3. An invalid selected path or malformed selected config returns a clear error and does not fall through to a lower-priority source.
4. A `.md` path is rejected as a canonical runtime path with guidance to use migration.
5. A valid profile saved to the selected path is read back by resources, tools, and prompts without restarting or selecting a sibling file.
6. If JSON is absent but Markdown exists, ordinary server reads report migration required and do not return Markdown content.
7. A successful migration produces Pydantic-valid JSON, preserves the Markdown source, creates its archive, and subsequent server reads use only JSON.
8. Malformed, unsupported, or semantically unmappable Markdown leaves the source untouched and produces no canonical JSON.
9. Migration refuses to overwrite an existing JSON profile and is safe to invoke again after success.
10. Simulated temporary-write, flush, `fsync`, and replace failures return failure, clean up temporary files when possible, and leave any prior valid destination intact.
11. The MCP stdio server still launches normally without migration arguments and uses the same selected canonical profile across all existing surfaces.
12. Documentation examples and environment setup snippets agree on `.json` as canonical and distinguish the profile path from MCP host configuration.

#### Stage 3 Acceptance Criteria

* All path-precedence, migration, atomic-write, and read-after-write tests pass.
* Tests prove runtime Markdown fallback has been removed and migration is the only Markdown reader.
* Existing unrelated MCP surface behavior remains covered by the current test suite.
* README, server setup, output prompt, architecture guide, and affected historical phase specs describe one consistent persistence contract.

---

## 6. Explicitly Out of Scope

* Runtime dual-format profile reads or dual authoritative writes.
* Automatic migration or other file mutation merely because the MCP server starts.
* Profile merging, profile conflict resolution, concurrent editing, or multi-user storage.
* SQLite, database infrastructure, network services, telemetry, authentication, or cloud synchronization.
* General-purpose backup rotation, automatic restore, or recovery systems beyond preserving the legacy source and its migration archive.
* Changes to the Phase 13 profile schema or question-bank, interview-state, and language-default issues unrelated to profile path selection.

---

## 7. Definition of Done

* [ ] `profile.json` is the sole canonical runtime profile and default location.
* [ ] All profile consumers use one resolver with CLI → `MYSPEC_PROFILE_PATH` → MySpec config → default precedence.
* [ ] `profile.md` is never loaded by normal server operation; legacy conversion is explicit, validated, and repeat-safe.
* [ ] Pydantic validation gates reads, migration output, and persistence using the Phase 13 model.
* [ ] Atomic writes use a same-directory temporary file and `os.replace`, preserving a prior valid destination on failure.
* [ ] Saving a canonical profile and reading it through every MCP surface returns the same updated data.
* [ ] All path, migration, failure, read-after-write, and documentation tests pass.
* [ ] No database or remote infrastructure is introduced.
