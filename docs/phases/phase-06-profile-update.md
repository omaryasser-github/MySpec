# Phase 6: Profile Update System & Skill-State Management

## Objective

Phase 6 defines the post-project process for auditing completed work against the current MySpec `profile.json`. The update engine uses verified delivery evidence to generate a new profile state while protecting the developer's core identity and separating proposed new skills from validated changes to existing skills.

## Profile State Management

- **Canonical current state:** `profile.json` is the current saved developer state and the baseline for each update cycle.
- **Evidence input:** The engine reviews completed project deliverables, applied technologies and patterns, and user clarification where implementation depth is unclear. Plans, backlog items, or intended work do not count as completed evidence.
- **Delta generation:** Compare confirmed project evidence with the current profile, classify each candidate change by semantic-versioning level, and produce a focused JSON delta plus changelog summary.
- **Next state:** Applying approved proposals and eligible validated skill changes produces the next profile state. Unchanged fields remain intact; each change must be traceable to evidence and its approval or application status.

## Semantic Versioning Policy

- **Major (`X.0.0`) — Core identity:** Fundamental identity and persona fields remain human-controlled. The update engine treats these fields as read-only and never changes a person's fundamental role or identity markers.
- **Minor (`X.Y.0`) — New skill extraction:** A technology or framework absent from the current profile is a candidate addition. The AI identifies it from completed work and returns it as a proposal. A human must explicitly approve the proposal before it is added to `profile.json`.
- **Patch (`X.Y.Z`) — Existing-skill validation:** For a skill already present in the profile, the AI may automatically update its proficiency score only when concrete evidence demonstrates implementation depth. The update must reflect observed practice, not mere exposure or a named dependency.

## Technical Workflow

1. **Load state:** Read the current canonical `profile.json` as the baseline. Preserve its unrelated historical fields.
2. **Extract evidence:** Identify technologies and patterns actually used in completed deliverables; record the artifact or implementation evidence for each candidate.
3. **Validate depth:** Compare evidence with the existing skill record. Distinguish deep implementation and independent problem-solving from surface-level use; ask focused technical questions when the evidence cannot support a proficiency decision.
4. **Classify changes:** Keep core identity fields unchanged; group newly demonstrated tools and skills as Minor proposals; group validated changes to existing skill scores as Patch updates.
5. **Generate delta:** Produce proposed additions separately from eligible auto-applied proficiency updates. Include a concise changelog that identifies evidence, version impact, and approval status.
6. **Form next state:** Apply only Patch updates supported by concrete evidence. Keep Minor additions pending explicit human approval, then merge approved additions without replacing unrelated profile data.
7. **Return update result:** Show the resulting versioned delta and the approval action still needed, if any. The new profile state becomes current only after the eligible patch updates and any approved additions are applied.

## Architectural Rationale

- **Protects identity ownership:** Major identity changes remain under human control because role and persona are personal facts rather than skills inferred from project artifacts.
- **Makes skill additions reviewable:** New technologies can be identified automatically while requiring human approval before they become durable profile facts.
- **Rewards demonstrated practice:** Patch updates keep proficiency current when completed work provides concrete evidence, without treating exposure as mastery.
- **Preserves profile continuity:** Delta-based updates change only supported fields and retain unrelated historical profile state.
- **Creates an auditable history:** Evidence references and a changelog make each profile update understandable and reversible by a reviewer.

## Acceptance Criteria

1. Each update starts from the existing `profile.json` and preserves fields that have no evidence-backed change.
2. Fundamental identity and role markers remain unchanged by the AI update engine.
3. New technologies and frameworks are returned as Minor proposals and are added only after explicit human approval.
4. Existing skill scores receive Patch updates only when completed deliverables show concrete implementation depth.
5. Plans and unimplemented work never produce skill increases.
6. Weak or ambiguous evidence triggers focused user questions rather than an unsupported score change.
7. The returned delta and changelog separate proposed, approved, and auto-applied changes and identify their evidence.

## Scope Boundary

Phase 6 covers profile update logic only: evidence extraction, semantic-version classification, delta generation, and resulting profile state. It does not define or implement MCP servers, external memory architecture, or project execution workflows.
