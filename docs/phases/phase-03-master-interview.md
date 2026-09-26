# Phase 3: Master Interview Logic & System Prompt Architecture

## Objective

Phase 3 turns the question matrices into a reusable `MySpec Profiler` system prompt. The prompt governs a conversational interview that collects a developer persona, summarizes each category, and emits a machine-readable profile when collection is complete.

## Scope

- **State-machine interview:** Track the active language, category, question IDs, pending pair, answered items, unresolved items, and clarification state. Present exactly two questions per turn; wait for the response before advancing. Summarize a completed category in two sentences before opening the next category.
- **Affirmative system constraints:** Use direct, positive instructions for turn-taking, redirection, omissions, language consistency, privacy-aware answers, and finalization. For off-topic requests, briefly acknowledge and restate the pending pair. For incomplete answers, ask for the missing response before advancing.
- **Few-shot prompting:** Include examples for off-topic redirection, a skipped question, and a contradiction that pauses progress pending clarification.
- **Contradiction detection:** Compare each new answer with facts collected in the current interview and any profile explicitly supplied by the user. Ask a neutral clarification when statements conflict; keep the affected state unresolved until clarified.
- **Answer trimming and memory summarization:** Condense verbose answers into concise, fact-dense memory while preserving qualifications, uncertainty, and user wording where meaning depends on it. The prompt uses a 100–300-word maximum per stored answer summary. The Phase 3 request also states a 200–400-word maximum; those ranges conflict and need a single product-wide limit before prompt versions are treated as canonical.
- **Strict JSON output:** After all questions and clarifications are complete, stop interviewing and return one raw JSON object with the seven profile keys: `identity`, `current_skills`, `learning_in_progress`, `limitations`, `communication_prefs`, `work_context`, and `growth_goals`.
- **Question-bank integration:** Reference the English and Arabic MSA matrices in `/questions`. Treat their headings and bullets as interview coverage cues, and map them to the seven output keys. Select a consistent target language at interview start and preserve it throughout.

## Acceptance Criteria

1. Every interview turn contains exactly two numbered questions, except category-completion summaries and a final profile response.
2. Interview progress waits for answers, resolves omissions and contradictions, and follows the seven categories in order.
3. Each completed category receives a two-sentence summary before the next category begins.
4. Final output parses as a single JSON object with exactly the documented top-level keys and no surrounding prose or Markdown fence.
5. The question bank provides 50 individually addressable questions with stable ordering and translation parity before the interview can be validated against a fixed 25-turn schedule.

## Known Dependencies and Gaps

The current question files provide topical bullets rather than 50 individually worded, numbered questions. The English files contain 51 topical headings, and the matrices' categories differ from the seven profile output keys. Phase 3 therefore defines prompt behavior and a mapping contract; it does not establish that a complete, count-verified 50-question bank already exists. The Egyptian Arabic matrix is present despite Phase 2's stated decision to exclude it; this prompt's supported language scope is English and Modern Standard Arabic.

The prompt is model-enforced guidance rather than a runtime state machine. Persistence across sessions, schema validation, and deterministic question counting require a host or integration layer.
