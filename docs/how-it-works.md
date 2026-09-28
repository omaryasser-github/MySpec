# How MySpec Works

## Phase 7 | System Workflow and User Utility

MySpec converts structured self-knowledge into reusable technical context. It begins with a 50-question interview across 7 categories, produces an actionable developer profile, applies that profile to project planning, and updates it from evidence gathered during completed work.

> [!IMPORTANT]
> MySpec is only as accurate as the evidence provided. Describe actual tools, responsibilities, decisions, constraints, and implementation depth. Specific evidence produces more useful profile guidance than unsupported skill labels.

## System Architecture

The system has one central profile and two operational feedback paths. The interview creates the profile, onboarding applies it before implementation, and profile update refines it after delivery.

```text
						+----------------------+
						| Existing AI Host    |
						| MCP client + model  |
						+----------+-----------+
								 | local stdio
								 v
						+----------------------+
						| MySpec MCP Server   |
						| resources, tools,   |
						| prompts (read-only) |
						+----------+-----------+
								 | local file read
								 v
						+----------------------+
						| ~/.myspec/profile.md|
						+----------------------+
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
				  | project_      |   | profile_update.md|
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

### 03 | `project_onboarding.md`

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

### 04 | `profile_update.md`

> **Role:** Evidence-based identity iteration

After a project is complete, profile update compares the current profile with completed deliverables, applied technologies, and verified implementation depth.

| Update class | Treatment |
| --- | --- |
| **Core identity** | Remains human-controlled and read-only for automated updates. |
| **New skill or tool** | Returned as a proposed addition requiring explicit approval. |
| **Existing skill** | May receive a proficiency update when concrete implementation evidence supports it. |
| **Unsupported plan** | Produces no skill increase because intended work is not delivery evidence. |

This creates a dynamic profile without restarting the master interview or silently rewriting the user's identity.

## The Engine: Local MCP Server

The local MCP server is a read-only stdio child process launched and owned by the user's existing AI host. The host is the MCP client: it discovers resources, calls tools, and selects prompts. The server reads `~/.myspec/profile.md` on demand (or `MYSPEC_PROFILE_PATH`) and exposes local context without implementing a separate client or server-side AI skill router.

| MCP surface | Local capability |
| --- | --- |
| Resources | `myprofile://summary`, `myprofile://skills`, `myprofile://preferences`, and `myprofile://full` provide focused views of the profile. |
| Tools | `get_gap_analysis(project_description)` returns local profile evidence and explicit technology-term matches; `get_onboarding_plan(topic, minutes=60)` returns a time-boxed learning outline. |
| Prompts | `onboarding(project_description)` and `gap_check(project_description)` package the project description and profile context for the host model. |
| Configuration | `MYSPEC_PROFILE_PATH` selects an alternate local file; `MYSPEC_LANG` selects English or MSA response labels. |

The server uses the local process and filesystem permissions as its trust boundary. It reads the profile without modifying it, uses stdio only, and makes no network calls. Missing or malformed profile files return readable status information so the host can continue with appropriate caveats.

> [!NOTE]
> The host controls model execution and any handling after it receives context. The MySpec server itself exposes no remote transport, authentication layer, or cloud integration.

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
