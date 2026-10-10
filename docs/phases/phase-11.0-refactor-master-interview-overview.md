# Phase 11.0: Master Interview Architecture & Refactoring Roadmap

> **Architectural Foundation & Source of Truth:**  
> This refactoring phase roadmap is derived directly from the canonical architectural specification defined in [`docs/master_interview_architecture.md`](../master_interview_architecture.md). All layer boundaries, component responsibilities, data contracts, and design principles established in that document govern the execution of Phases 11.0 through 11.4.

---

## 1. Executive Summary & Problem Statement

In the initial implementation of MySpec, the **Master Interview** process existed solely as a monolithic, 505-line prompt (`prompts/master-interview.md`). This architecture suffered from three fundamental structural limitations:

1. **Triple Duplication of Questions:** The 50 canonical interview questions existed in three disparate locations simultaneously:
   - `questions/EN/*.md` (7 Markdown files)
   - `questions/AR-MSA/*.md` (7 Arabic Markdown files)
   - `prompts/master-interview.md` (lines 137–504, an embedded 380-line `<QUESTIONS_BANK>`)
   Any update or localization fix in `questions/` drifted away from the prompt copies.

2. **Manual Web Chat Dependency:** Triggering `/master-interview start` required a user to manually copy and paste 41 KB of prompt text into a web LLM interface (ChatGPT/Claude Web), answer 25 turns manually, copy the resulting JSON, and manually create `~/.myspec/profile.json` on disk.

3. **Disconnection from Local MCP Server:** The `myspec-local-mcp-server` was 100% read-only. It had no mechanism to serve questions, collect answers, or persist profiles, despite MySpec Core having tools (`get_gap_analysis`, `get_onboarding_plan`) and resources (`myprofile://...`) waiting to consume that profile data.

### The Target Solution
Refactor the system into a **5-layer modular pipeline** where:
- `questions/` is the **exclusive single source of truth (SSOT)**.
- `myspec_mcp_server` dynamically loads questions pair-by-pair via MCP tools.
- User answers are assembled and atomically written to `~/.myspec/profile.json`.
- MySpec Core instantly and automatically reads the generated profile with zero configuration.

---

## 2. Architectural Blueprint & Data Flow

```
USER types: /master-interview start
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              MCP Server (server.py)                       │
│  Tool: start_interview(language="en")                     │
│    → queries questions.py: get_question_pair(pair_index=0)│
│    → returns [Q01, Q02] + session metadata               │
└──────────────┬───────────────────────────────────────────┘
               │ (AI Host presents questions to user)
               ▼
         User answers Q01 & Q02
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  Tool: advance_interview(pair_index, answers_so_far)      │
│    → queries questions.py for next pair                  │
│    → validates progression (turns 0 to 24)               │
│    → returns next pair OR {status: "interview_complete"} │
└──────────────┬───────────────────────────────────────────┘
               │ (Repeats for 25 turns / 50 questions)
               ▼
        All 50 questions answered
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  Tool: finalize_interview(answers)                        │
│    → calls profile.py: build_profile(answers)             │
│    → calls profile.py: save_profile(data) [Atomic Write]  │
│    → returns {status: "saved", path: "~/.myspec/..."}     │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
       ~/.myspec/profile.json (written to disk)
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│         MySpec Core (Existing Surfaces)                   │
│  myprofile://skills          myprofile://summary          │
│  get_gap_analysis()          get_onboarding_plan()        │
│  onboarding()                gap_check()                  │
└──────────────────────────────────────────────────────────┘
```

---

## 3. Layer Responsibility Model

| Layer | Module / Artifact | Status | Primary Responsibility |
| :--- | :--- | :--- | :--- |
| **Layer 1: Data Bank** | `questions/EN/*.md`<br>`questions/AR-MSA/*.md` | **Existing (SSOT)** | Canonical source for all 50 questions across 7 categories. No other file duplicates question text. |
| **Layer 2: Parser** | `myspec_mcp_server/questions.py` | **New (Phase 11.1)** | Question bank parser, file path resolver, and pair slicing engine. Zero business logic. |
| **Layer 3: Domain & I/O** | `myspec_mcp_server/profile.py` | **Extend (Phase 11.2)** | Schema validation, `build_profile()`, atomic `save_profile()`, and existing `load_profile()`. |
| **Layer 4: Transport** | `myspec_mcp_server/server.py` | **Extend (Phase 11.3)** | MCP protocol tools: `start_interview`, `advance_interview`, `finalize_interview`. Stateless request validation. |
| **Layer 5: Orchestration** | `prompts/master-interview.md`<br>`prompts/master-interview-standalone.md` | **Refactor (Phase 11.4)** | Lean workflow orchestration instructions for AI hosts, plus separate standalone copy for web LLM paste usage. |

---

## 4. Phase Breakdown & Execution Sequence

```
Phase 11.1: Canonical Question Bank Engine (questions.py)
  │   - Parse questions/EN and questions/AR-MSA into Question objects
  │   - Implement get_question_pair() and category mappings
  │   - Unit tests: test_questions.py
  ▼
Phase 11.2: Profile Assembly & Atomic Persistence (profile.py)
  │   - Implement build_profile(answers) mapping Q01–Q50 to 7 modules
  │   - Implement save_profile() using atomic tmp-file rename pattern
  │   - Unit tests: test_profile.py
  ▼
Phase 11.3: MCP Tool Surface & Stateless State Machine (server.py)
  │   - Register start_interview, advance_interview, finalize_interview
  │   - Maintain client-side stateless state accumulation
  │   - Update test_server.py assertions & verify MCP client execution
  ▼
Phase 11.4: Prompt Decoupling & End-to-End Verification
      - Strip 380-line embedded question bank from master-interview.md
      - Create master-interview-standalone.md for web LLM backwards compatibility
      - Full regression suite execution across EN and AR
```

---

## 5. Non-Breaking Safety Guarantees

1. **Zero Impact on Existing MCP Surfaces:**
   - All 4 resources (`myprofile://summary`, `myprofile://skills`, `myprofile://preferences`, `myprofile://full`) remain completely untouched.
   - Existing tools (`get_gap_analysis`, `get_onboarding_plan`) and prompts (`onboarding`, `gap_check`) maintain their exact schemas and behaviors.
2. **Local-Only & Zero-Network Guarantee:**
   - The refactored code relies entirely on local filesystem access and Python stdlib. No cloud dependencies or databases.
3. **Atomic File Safety:**
   - Writing `profile.json` will strictly utilize temporary files and atomic `replace()` operations to prevent file corruption during system interruptions.
4. **Test-Driven Progression:**
   - No phase will be considered complete until its corresponding unit test suite passes with 100% green status.
