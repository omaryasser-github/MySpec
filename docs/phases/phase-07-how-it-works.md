# Phase 7: MySpec Workflow Documentation

## Objective

Phase 7 documents how the completed MySpec system works as a connected workflow and explains how users can get practical value from it. The documentation turns the project's separate prompts and profile concepts into one understandable lifecycle: discover the user's experience, generate a reusable profile, apply that profile to project planning, and update it from verified work. It also presents the system core through structured Markdown layouts, callouts, tables, and a text-based architecture flow.

## Documentation Delivered

- **Primary guide:** Created `docs/how-it-works.md` as the user-facing overview of the MySpec workflow.
- **Phase overview:** Explained how MySpec captures working context, turns it into reusable profile data, applies it to project decisions, and keeps it current as the user grows.
- **Value guidance:** Advised users to provide concrete examples, tools, decisions, level of involvement, and constraints so the system can produce evidence-based recommendations.
- **Workflow summary:** Added a four-stage progression: Discover, Define, Apply, and Grow.
- **Core file guide:** Documented the role and benefit of `master-interview.md`, the profile output file, `project-onboarding.md`, and `profile-update.md`.
- **Architecture visualization:** Added a clean text-based flow showing the profile lifecycle and the MCP Server's position as the central orchestration engine.
- **Engine explanation:** Documented how the MCP Server connects the files through AI skills, prompt triggers such as `/skill-name`, and context transfer between stages without repeated manual setup.
- **Presentation system:** Used alert blocks, structured file cards, high-contrast tables, and compact Markdown grids to make the system core easy to scan.

## Core Workflow

1. **Discover:** `master-interview.md` conducts a structured interview of 50 questions across seven categories. Answers are progressively summarized while preserving relevant context.
2. **Define:** The confirmed interview facts become the canonical profile output. The profile represents skills, depth of experience, decision-making style, work context, communication preferences, limitations, learning areas, and growth goals.
3. **Apply:** `project-onboarding.md` compares the canonical profile with a new project's requirements. It produces a profile-aware gap analysis, effort and timeline estimate, learning plan, risk assessment, and expected skill gains.
4. **Grow:** `profile-update.md` reviews completed project work and supporting evidence. It proposes new skills for approval and validates deeper proficiency in existing skills when implementation evidence supports the change.

Each stage feeds the next. The profile is created once, reused across projects, and improved from completed work rather than rebuilt from the beginning.

## Core File Responsibilities

| File or artifact | Responsibility | User benefit |
| --- | --- | --- |
| `master-interview.md` | Collects 50 questions across seven categories and progressively summarizes answers. | Captures a structured and useful representation of how the user works. |
| Profile output file | Stores the user's core identity, skills, experience depth, and decision-making style. | Provides a reusable source of truth for personalized assistance. |
| `project-onboarding.md` | Matches the profile against project requirements and identifies gaps, effort, risks, and learning needs. | Makes project planning more realistic and relevant to the user's starting point. |
| `profile-update.md` | Audits completed work and prepares evidence-based profile changes. | Keeps the profile current without repeating the master interview. |

## Architecture Visualization

The MySpec architecture is organized as a text-based sequence:

1. `master-interview.md` collects 50 questions across seven categories and progressively summarizes the user's confirmed answers.
2. The Profile Output File stores the resulting skills, technical depth, decision-making style, and relevant work context as the canonical source of truth.
3. `project-onboarding.md` reads the profile before implementation and performs a strategic gap analysis against the new project's requirements.
4. `profile-update.md` reads completed project evidence after delivery and prepares approved or evidence-backed profile changes.
5. The MCP Server coordinates these stages by routing context through AI skills and prompt triggers.

## User Utility Guidelines

- Give specific examples instead of naming a skill without context.
- Describe what was implemented personally, how independently it was done, and what decisions were involved.
- Include constraints such as deadlines, available time, preferred tools, and project limitations.
- Treat onboarding estimates as planning information and review their assumptions before implementation.
- Use completed deliverables and observable outcomes as evidence for profile growth; plans and unimplemented work are not enough.
- Keep core identity under human control while reviewing proposed skill additions and validated proficiency changes.

## The Engine

The MCP Server connects the documented files dynamically through AI skills. It routes the relevant profile, project, and evidence context to the appropriate prompt, allowing the interview, onboarding, and update workflows to work together without requiring the user to manually configure each handoff.

The engine coordinates the workflow; it does not replace user confirmation where the system requires ownership, clarification, or approval.

## Architectural Rationale

- **Makes the system understandable:** A single guide explains how the individual prompts form one product rather than isolated documents.
- **Improves personalization:** Users are shown what information produces stronger profile-aware results.
- **Preserves continuity:** The workflow reuses the canonical profile across projects and updates it through evidence.
- **Separates responsibilities:** Interviewing, profile generation, project onboarding, and profile updating each retain a clear purpose.
- **Protects user ownership:** Identity remains human-controlled, and proposed skill additions remain reviewable before becoming durable profile facts.
- **Reduces setup friction:** Dynamic MCP Server connections remove the need for repeated manual context wiring.

## Acceptance Criteria

1. `docs/how-it-works.md` introduces MySpec and explains how to extract practical value from it.
2. The guide describes the workflow from interview through profile generation, project onboarding, and profile update.
3. The guide documents `master-interview.md` as the starting point with 50 questions across seven categories and progressive summarization.
4. The guide documents the profile output as the user's core identity, including skills, depth, and decision-making style.
5. The guide documents `project-onboarding.md` as the profile-to-project gap-analysis tool.
6. The guide documents `profile-update.md` as the mechanism for dynamic, evidence-based profile growth without restarting.
7. The guide explains that the MCP Server connects the files dynamically through AI skills and prompt triggers.
8. The guide includes a readable text-based architecture flow with the MCP Server represented as the central engine.
9. The guide uses callouts, tables, structured file cards, and professional technical English.

## Scope Boundary

Phase 7 covers user-facing workflow documentation and the explanation of how the existing MySpec components work together. It does not implement the MCP Server, change the interview rules, alter profile schemas, execute project onboarding, or persist profile updates.
