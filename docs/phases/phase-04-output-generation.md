# Phase 4: Canonical Profile Generation & Memory Persistence

## Objective

Phase 4 defines the post-interview output layer in `output/output_generation_prompt.md`. It turns confirmed interview answers into a validated, reusable profile, supports updates to an existing profile, and routes requested Arabic exports from a stable English source.

## Output Engine Architecture

- **Dedicated system prompt:** Established the `MySpec Output & Memory Persistence Engine` as the handoff target after interview fact collection. The output engine receives confirmed answers, dispositions, question IDs, completion state, an optional previous profile, and the output preference.
- **Canonical English profile:** Defined `profile.json` as the primary, canonical source of truth (SSOT). It contains metadata and seven structured modules: `identity`, `current_skills`, `learning_in_progress`, `limitations`, `communication_prefs`, `work_context`, and `growth_goals`.
- **Versioned validation contract:** Added a Pydantic v2 model and a matching JSON Schema. The contract specifies `schema_version`, timezone-aware `completed_at`, `status`, bounded `completion_rate`, `output_preference`, unique `skipped_fields`, and all seven module dictionaries.
- **Completion tracking:** Defined `complete`, `partial`, and `stale` states. Stable question IDs make skipped core questions visible; the completion rate is calculated against the canonical set of 50 questions. A profile with unresolved core questions is marked partial.
- **Profile updates:** Specified a deep-merge and JSON Patch workflow for existing profiles. New answers update only their mapped paths, explicit corrections replace prior values, and unchanged historical answers remain intact. Reapplying the same answers is idempotent.
- **Localized exports:** Defined Arabic output as a downstream translation of canonical English (`arabic = translate(canonical_english)`). When requested, the engine produces `profile_ar.json` and `profile_ar.md`, preserving technical identifiers and stable JSON keys.
- **Output routing:** `english_only` is the default. `english_only` and `none` emit the canonical profile only; `bilingual` and `arabic_only` retain the canonical profile and generate the Arabic exports. The `arabic_only` choice controls user-facing exports and does not replace the English SSOT.

## Architectural Rationale

- **One authoritative profile:** A canonical English representation avoids divergence between languages and gives later tools a predictable data source.
- **Safe incremental updates:** Deep merge, explicit correction semantics, and idempotency let users update a profile without losing unrelated historical context or duplicating list values.
- **Machine-readable completeness:** Metadata and stable skipped-question IDs communicate profile freshness and coverage to downstream consumers instead of hiding partial data.
- **Separation of concerns:** The interview prompt gathers and summarizes facts; the output prompt validates, persists, merges, and localizes them. This keeps conversation flow separate from profile lifecycle rules.
- **Consistent localized artifacts:** Deriving Arabic JSON and Markdown from the canonical profile preserves meaning, schema keys, technical terms, and one-way source-of-truth ownership.

## Intended Data Flow

1. Receive confirmed interview answers and, when present, the previous canonical profile.
2. Merge new facts into the prior profile or initialize a new one.
3. Recompute skipped question IDs, completion rate, and status.
4. Validate the complete canonical object against the Pydantic contract and JSON Schema.
5. Persist and emit canonical English `profile.json`.
6. For `bilingual` or `arabic_only`, translate the canonical values into MSA and emit `profile_ar.json` and `profile_ar.md`.

## Acceptance Criteria

1. Every emitted canonical profile contains the metadata fields and all seven module dictionaries required by the schema.
2. `completed_at` is an ISO 8601 timestamp with timezone; `completion_rate` stays in the range 0.0–1.0.
3. Unresolved core question IDs appear in `skipped_fields` and result in `status: "partial"`.
4. An update preserves historical answers unless the user provides a new answer or explicit correction for that field.
5. Replaying the same update produces the same profile content, completion state, and skipped question IDs.
6. Arabic exports are generated only for `bilingual` or `arabic_only`, retain the canonical schema keys, and remain derived from English.

## Dependencies and Implementation Boundary

The Pydantic model and JSON Schema are currently specified inside a system prompt; this phase does not add a runtime validator, persistence service, or file-writing integration. Enforcement therefore depends on the host system or a future implementation. The completion calculation also depends on a canonical, stable 50-question bank, while the current question matrices remain topic outlines. Those components are prerequisites for deterministic validation and reproducible completion rates.
