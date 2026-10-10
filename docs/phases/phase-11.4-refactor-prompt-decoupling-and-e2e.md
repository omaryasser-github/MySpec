# Phase 11.4: Prompt Decoupling & End-to-End Verification

> **Architectural Foundation & Source of Truth:**  
> This specification is derived directly from [`docs/master_interview_architecture.md`](../master_interview_architecture.md), specifically addressing **Q2 (Refactoring master-interview.md to Workflow Only)**, **Q10 (Connecting Interview & MySpec Core)**, and **Layer 4 & 5 (Orchestration & Question Bank Boundaries)**.

---

## 1. Objective

Complete the architectural refactoring by decoupling prompt definitions from the raw question data:
1. Streamline `prompts/master-interview.md` by stripping the 380-line embedded `<QUESTIONS_BANK>` duplicate, transforming it into a lean (~120-line) orchestration specification for AI hosts connected to the MCP server.
2. Create `prompts/master-interview-standalone.md` retaining the embedded bank to preserve 100% backwards compatibility for web chat users (ChatGPT/Claude Web) who lack MCP server access.
3. Perform end-to-end regression testing across the entire MySpec ecosystem to guarantee zero regressions.

---

## 2. Scope & Target Files

* **Modify**: `prompts/master-interview.md` (Strip `<QUESTIONS_BANK>`, retain orchestration rules)
* **Create**: `prompts/master-interview-standalone.md` (Self-contained distribution for web LLMs)
* **Verify**: `mcp-server/tests/` (Full test suite execution across all modules)

---

## 3. Technical Specifications

### 3.1 Refactoring `prompts/master-interview.md`
The primary `master-interview.md` prompt becomes an **orchestration specification** rather than a bloated data container:
- **Retain Sections:**
  - Role and Purpose definition
  - Operating Principles (2 questions per turn, evidence collection, no preaching)
  - State Machine definition (States 0 through 7)
  - Category-to-Profile module mapping matrix
  - Off-topic, refusal, and omission handling guidelines
  - Few-shot conversation examples
- **Remove Sections:**
  - The monolithic `<QUESTIONS_BANK>` XML block (lines 137–504).
- **Add Orchestration Directive:**
  ```markdown
  ## Dynamic Question Sourcing
  Questions are loaded dynamically from the local question bank via the MySpec MCP Server.
  The host AI model interacts with the interview engine using:
  1. `start_interview` to receive the initial turn pair (Q01, Q02).
  2. `advance_interview` to submit accumulated user answers and fetch subsequent pairs.
  3. `finalize_interview` upon completing all 25 turns to build and persist ~/.myspec/profile.json.
  ```

### 3.2 Standalone Web Distribution (`master-interview-standalone.md`)
To maintain the core MySpec principle that users without local developer environments can still generate profiles via web chat:
- Copy the complete, self-contained original prompt to `prompts/master-interview-standalone.md`.
- Maintain the embedded `<QUESTIONS_BANK>` in this standalone artifact.
- Add an explanatory header clarifying that this file is intended exclusively for manual copy-paste into web interfaces (ChatGPT, Claude, Gemini).

---

## 4. End-to-End System Verification Matrix

After completing Phases 11.1 through 11.4, perform the comprehensive full-system verification:

### 4.1 Automated Test Discovery
Execute the entire test suite from `mcp-server/`:
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
All tests across `test_questions.py`, `test_profile.py`, and `test_server.py` must pass with zero errors and zero warnings.

### 4.2 Bilingual Verification
- Verify execution under English default: `MYSPEC_LANG=en`.
- Verify execution under Arabic MSA: `MYSPEC_LANG=ar`.
- Ensure question prompt extraction, localization, and resource rendering (`myprofile://summary`) operate smoothly without encoding issues (`UTF-8` compliance).

### 4.3 Full Lifecycle Smoke Test
1. Spawn MCP server in stdio mode.
2. Call `start_interview` $\rightarrow$ verify Q01 and Q02 returned.
3. Call `advance_interview` $\rightarrow$ simulate answering pairs across multiple categories.
4. Call `finalize_interview` $\rightarrow$ verify `profile.json` is atomically created on disk.
5. Query MySpec Core surfaces:
   - Call `client.read_resource("myprofile://full")` $\rightarrow$ returns profile data.
   - Call `client.call_tool("get_gap_analysis", {"project_description": "..."})` $\rightarrow$ performs gap analysis against the newly created profile.

---

## 5. Acceptance Criteria & Definition of Done

* [ ] `prompts/master-interview.md` is reduced to a concise (~120-line) orchestration specification.
* [ ] `prompts/master-interview-standalone.md` is available and functionally complete for web LLM usage.
* [ ] Question duplication across the repository is eliminated (`questions/` is the sole SSOT).
* [ ] 100% of automated tests pass in the MCP server test suite.
* [ ] No existing MCP resources, tools, or prompt contracts are broken.
