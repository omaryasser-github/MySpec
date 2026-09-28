# How MySpec Works

## Phase 7 | System Workflow and User Utility

MySpec converts structured self-knowledge into reusable technical context. It begins with a 50-question interview across 7 categories, produces an actionable developer profile, applies that profile to project planning, and updates it from evidence gathered during completed work.

> [!IMPORTANT]
> MySpec is only as accurate as the evidence provided. Describe actual tools, responsibilities, decisions, constraints, and implementation depth. Specific evidence produces more useful profile guidance than unsupported skill labels.

## System Architecture

The system has one central profile and two operational feedback paths. The interview creates the profile, onboarding applies it before implementation, and profile update refines it after delivery.

```text
						+----------------------+
						|     MCP Server       |
						|  AI skills + routing |
						|  prompt triggers     |
						+----------+-----------+
								 |
								 v
+----------------------+      +---------+----------+
| master-interview.md  | ---> |   Profile Output   |
| 50 questions /       |      |   Source of Truth  |
| 7 categories         |      | skills + depth     |
+----------------------+      | decision style     |
						+----+-----------+---+
							|           |
				before work    |           | after work
							v           v
				  +------------+--+   +----+-------------+
				  | project-      |   | profile-update.md|
				  | onboarding.md |   | evidence-based   |
				  | gap analysis  |   | profile growth   |
				  +---------------+   +------------------+
```

> [!NOTE]
> The profile is the canonical context layer. It should be reused across projects and changed through explicit, evidence-based updates rather than recreated for every new engagement.

## Workflow Overview

| Stage | System action | Practical output |
| --- | --- | --- |
| **01 Discover** | Conduct the ordered interview and preserve confirmed answers, uncertainty, and clarifications. | High-fidelity interview record |
| **02 Define** | Progressively summarize the interview into structured profile fields. | Actionable developer profile |
| **03 Apply** | Compare project requirements with profile evidence and classify capability gaps. | Personalized onboarding plan |
| **04 Deliver** | Use the plan to guide implementation, learning, and risk management. | Completed project evidence |
| **05 Grow** | Compare verified delivery evidence with the current profile. | Proposed or applied profile delta |

## Core Files and Their Value

### 01 | `master-interview.md`

> **Role:** Progressive discovery and data-fidelity control

| Capability | How it works | Why it matters |
| --- | --- | --- |
| Structured coverage | Asks 50 questions across 7 categories in a defined order. | Reduces blind spots across identity, communication, skills, workflow, decisions, goals, and context. |
| Progressive summarization | Condenses each answer into a fact-dense working summary while the interview advances. | Preserves signal without producing an unusably large profile. |
| Category summaries | Summarizes each completed category and marks unresolved uncertainty. | Makes the collected information reviewable before profile generation. |
| Clarification handling | Pauses on meaningful conflicts or ambiguous answers rather than inferring facts. | Protects the fidelity of the final profile. |

> [!TIP]
> Provide one concrete example when possible: the problem, your responsibility, the technology involved, the decision you made, and the result. This gives the interview evidence it can summarize accurately.

### 02 | Profile Output File

> **Role:** Canonical source of truth for personalization

The profile output consolidates the interview into an actionable developer identity. Its most important dimensions are:

| Profile dimension | What it represents |
| --- | --- |
| **Core skills** | Technologies, tools, and practices the user can apply. |
| **Technical depth** | The difference between exposure, working knowledge, and independently demonstrated proficiency. |
| **Decision-making style** | How the user evaluates trade-offs, handles uncertainty, and chooses implementation paths. |
| **Work context** | Environment, responsibilities, constraints, and preferred ways of working. |
| **Growth direction** | Current learning areas and longer-term goals that should influence project recommendations. |

> [!IMPORTANT]
> Treat the canonical profile as the source of truth for downstream workflows. Derived or localized outputs should remain consistent with the canonical profile rather than becoming competing records.

### 03 | `project-onboarding.md`

> **Role:** Strategic project-to-profile integration

Before implementation begins, project onboarding maps each material requirement to profile evidence. It identifies what is ready, what requires a refresher, what represents a skill gap, and what remains unknown.

| Analysis area | Value delivered |
| --- | --- |
| Requirement mapping | Connects project outcomes and technical requirements to relevant profile evidence. |
| Gap analysis | Shows the minimum capability needed, transferability, and consequence of each gap. |
| Effort estimation | Applies skill multipliers, dependencies, capacity, and explicit contingency. |
| Pre-flight learning | Prioritizes time-boxed learning with observable readiness checks. |
| Risk assessment | Identifies critical-path risks, bottlenecks, single points of failure, and over-engineering. |

The result is a project plan calibrated to the user's actual starting point rather than a generic checklist.

### 04 | `profile-update.md`

> **Role:** Evidence-based identity iteration

After a project is complete, profile update compares the current profile with completed deliverables, applied technologies, and verified implementation depth.

| Update class | Treatment |
| --- | --- |
| **Core identity** | Remains human-controlled and read-only for automated updates. |
| **New skill or tool** | Returned as a proposed addition requiring explicit approval. |
| **Existing skill** | May receive a proficiency update when concrete implementation evidence supports it. |
| **Unsupported plan** | Produces no skill increase because intended work is not delivery evidence. |

This creates a dynamic profile without restarting the master interview or silently rewriting the user's identity.

## The Engine: MCP Server Integration

The MCP Server acts as the orchestration layer between the profile and the operational prompts. It dynamically supplies the relevant context, selects the appropriate AI skill, and routes the result to the next stage.

| Engine responsibility | System effect |
| --- | --- |
| Context loading | Provides the profile, project brief, constraints, or completed-work evidence required by the active workflow. |
| Skill routing | Invokes the appropriate AI skill for interview, output generation, onboarding, or profile update. |
| Prompt triggering | Supports explicit triggers such as `/skill-name` to select a workflow without manual context assembly. |
| State continuity | Carries confirmed facts, profile state, and workflow results between connected stages. |
| Human control | Preserves required clarification, approval, and identity ownership boundaries. |

> [!NOTE]
> The engine removes repeated setup work; it does not remove the user's authority over personal identity, ambiguous facts, proposed skill additions, or final profile state.

## Best Practices for Maximum Utility

1. **Use evidence, not labels.** Replace "advanced in Python" with the systems built, responsibilities held, and problems solved.
2. **Describe depth precisely.** Distinguish reading, guided practice, assisted implementation, independent delivery, and ownership in production.
3. **State constraints.** Include time availability, deadlines, team size, preferred stack, budget, access limitations, and external dependencies.
4. **Explain decisions.** Record why a tool, architecture, trade-off, or workflow was selected and what alternatives were rejected.
5. **Preserve uncertainty.** Say when information is unknown or context-dependent. A declared unknown is more useful than an invented certainty.
6. **Separate plans from outcomes.** Do not present planned, tutorial-only, or unimplemented work as completed proficiency evidence.
7. **Review generated assumptions.** Check onboarding estimates, risk classifications, and learning plans before treating them as commitments.
8. **Update after delivery.** Supply shipped artifacts, implementation details, test results, operational outcomes, and personal reflection for profile updates.

## Operating Principle

> [!TIP]
> **Interview once. Reuse the profile. Plan with evidence. Update from delivery.**
>
> This cycle is the practical value of MySpec: a structured understanding of how the user works becomes better technical guidance over time.
