# Phase 5: Project Onboarding & Personalized Delivery Planning

## Objective

Phase 5 defines how MySpec evaluates a proposed project against a developer's canonical profile before implementation starts. The workflow identifies relevant strengths and skill gaps, estimates effort and schedule with explicit buffers, creates a focused pre-flight learning plan, maps expected skill acquisition to career goals, and prepares an evidence-based profile sync after project completion.

## Project Onboarding Architecture

- **Dedicated operational prompt:** Created `prompts/project_onboarding.md` for an LLM to analyze a project brief or PRD alongside the user's MySpec JSON profile and delivery constraints.
- **Context injection:** Treat the canonical English profile as the source for skills, work context, limitations, communication preferences, and growth goals. Missing profile or PRD details remain unknown or become clearly labeled assumptions.
- **Competency mapping:** Map each material requirement to supporting profile evidence and classify it as `Ready to Go (Proficient)`, `Refresher Needed (Intermediate)`, `Learning Curve (Skill Gap)`, or `Unknown` when evidence is insufficient.
- **Effort weighting:** Estimate baseline person-effort and apply 1.0x for proficient work, 1.3x–1.5x for refreshers, and at least 2.0x for new skills. Show the calculation and confidence for each estimate.
- **Timeline buffering:** Model dependencies, critical-path work, parallelism, weekly capacity, and an explicit contingency buffer. Separate person-hours from elapsed calendar time and avoid counting learning effort twice.
- **Pre-flight learning plan:** Prioritize learning that reduces critical-path uncertainty. Give each item a time box, practice activity, and observable readiness check before implementation.
- **Career value and acquisition:** List the practical skills the project can build and connect them to the developer's stated growth goals without promising career outcomes.
- **Risk and bottleneck assessment:** Identify integration risks, over-engineering pressure, bottlenecks, and single points of failure (SPOFs), including triggers, mitigations, and fallbacks.
- **Post-project profile sync:** After completion, use shipped work and user-confirmed reflection to propose narrow updates to demonstrated skills and relevant goals while preserving unrelated profile history.

## Technical Workflow

1. **Inject context:** Load the project brief/PRD, canonical profile, and delivery constraints such as deadline, available hours, team size, and dependencies.
2. **Extract requirements:** Identify outcomes, features, technical requirements, acceptance criteria, deliverables, and external dependencies.
3. **Compare the profile:** Match requirements to skill evidence and classify each competency, marking unsupported or missing evidence as unknown.
4. **Identify gaps and risks:** Find the learning curve, critical-path risks, bottlenecks, SPOFs, and scope that may exceed the PRD's actual needs.
5. **Calculate effort and buffers:** Estimate baseline tasks, apply skill multipliers, account for dependencies, add explicit contingency, then convert person-effort into a schedule using stated capacity.
6. **Prepare pre-flight learning:** Prioritize time-boxed study and practice with readiness checks for the highest-impact gaps.
7. **Report before execution:** Present the project fit, competency map, estimates, learning plan, career value, and mitigations. Onboarding itself remains a planning step and does not start implementation.
8. **Sync after completion:** Assess completed work and evidence, then propose a minimal profile merge or JSON Patch for user confirmation or an authorized persistence integration.

## Estimate Model

- **Adjusted task effort:** `baseline effort × skill multiplier`.
- **Adjusted total:** Sum adjusted task effort and explicitly scoped integration, testing, review, deployment, and documentation work.
- **Buffered effort:** `adjusted total × (1 + contingency rate)`, with the rate justified by uncertainty and dependency risk.
- **Elapsed time:** Convert buffered person-effort into calendar time using weekly capacity and dependency/parallelization assumptions.
- **Learning accounting:** Include ramp-up either in the multiplier or as a separate pre-flight task, and state which method is used so the same effort is counted once.

## Architectural Rationale

- **Personalized feasibility:** Mapping requirements to profile evidence provides a more useful plan than a generic estimate.
- **Visible uncertainty:** Explicit classifications, multipliers, confidence, and assumptions show where the estimate depends on learning or missing information.
- **Planned skill acquisition:** Time-boxed learning and readiness checks help reduce critical-path risk before coding begins.
- **Career-aware planning:** Showing expected skill gains helps the developer weigh delivery effort against their stated long-term direction.
- **Controlled scope:** Keeping the current stack by default and flagging unnecessary complexity protects the project from avoidable migration and over-engineering.
- **Evidence-based profile growth:** Post-project updates distinguish demonstrated proficiency from exposure, preserve historical data, and avoid silently changing the canonical record.

## Acceptance Criteria

1. Every material project requirement maps to profile evidence or is marked unknown with its impact stated.
2. Skills use the defined readiness categories and show the evidence behind each classification.
3. Estimates show baseline effort, multiplier, adjusted effort, contingency, capacity, dependencies, and elapsed-time assumptions.
4. The pre-flight learning plan prioritizes high-impact gaps with time boxes and measurable readiness checks.
5. The report identifies career-relevant skill gains, over-engineering risks, bottlenecks, SPOFs, and mitigations.
6. The onboarding prompt does not begin implementation or claim unsupported profile changes.
7. A post-project patch is limited to evidence-backed updates and preserves unrelated historical answers.

## Dependencies and Implementation Boundary

Useful personalization depends on a canonical profile with specific skill and growth-goal evidence, a PRD with testable requirements, and realistic schedule and capacity inputs. The onboarding file is an LLM operational prompt; deterministic estimation, project execution, and persistent profile updates require a host implementation or explicit authorized integration. The stable 50-question ID set referenced by profile completion metadata also remains a prerequisite for consistent profile coverage signals.
