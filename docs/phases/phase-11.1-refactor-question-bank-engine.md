# Phase 11.1: Canonical Question Bank Engine (`questions.py`)

> **Architectural Foundation & Source of Truth:**  
> This specification is derived directly from [`docs/master_interview_architecture.md`](../master_interview_architecture.md), specifically addressing **Q1 (Single Source of Truth)**, **Q4 (Internal Question Loading)**, **Q5 (Language & Category Selection)**, and **Layer 1 (Question Bank Loader)**.

---

## 1. Objective

Establish `questions/` as the single canonical source of truth for all 50 interview questions across both supported languages (`EN` and `AR-MSA`). Implement a robust, zero-external-dependency Python engine in `mcp-server/src/myspec_mcp_server/questions.py` that parses the markdown files at runtime, structures question entities, provides category metadata, and generates question pairs for the 25 interview turns.

---

## 2. Scope & Target Files

* **Create**: `mcp-server/src/myspec_mcp_server/questions.py` (Parser and question bank engine)
* **Create**: `mcp-server/tests/test_questions.py` (Isolated unit test suite)
* **Reference**: `questions/EN/*.md` (7 canonical English category files)
* **Reference**: `questions/AR-MSA/*.md` (7 canonical Arabic category files)

---

## 3. Technical Specifications

### 3.1 Path Resolution Contract
The loader must locate the `questions/` directory safely regardless of the current working directory from which the MCP server process is spawned by an AI host (e.g., Cursor, Claude Desktop, VS Code):

```python
def get_questions_root() -> Path:
    """Resolve the canonical questions root directory.
    
    1. Checks MYSPEC_QUESTIONS_PATH environment variable override.
    2. Falls back to package-relative path: <package_root>/../../../questions
    """
```

### 3.2 Question Data Structure
Define an immutable data contract for parsed questions:

```python
from typing import TypedDict

class Question(TypedDict):
    id: str               # "Q01", "Q02", ..., "Q50"
    category_id: int      # 1 to 7
    category_name: str    # e.g., "Identity & Work"
    title: str            # e.g., "Current Role and Primary Domain"
    prompt: str           # The verbatim question text
    language: str         # "en" or "ar"
    target_modules: list[str] # Profile modules affected, e.g. ["identity", "work_context"]
```

### 3.3 Category Metadata and Profile Mapping
Embed the canonical category lookup table as an immutable module constant:

| Category ID | Name (EN) | File Name Pattern | ID Range | Target Profile Modules |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Identity & Work | `01-identity-work{suffix}.md` | Q01–Q10 | `identity`, `work_context` |
| **2** | Communication Style | `02-communication-style{suffix}.md` | Q11–Q18 | `communication_prefs` |
| **3** | Knowledge & Skills | `03-knowledge-and-skills{suffix}.md` | Q19–Q25 | `current_skills`, `learning_in_progress`, `limitations` |
| **4** | Tools & Workflows | `04-tools-and-workflows{suffix}.md` | Q26–Q32 | `current_skills`, `work_context`, `limitations` |
| **5** | Decision-Making | `05-decision-making{suffix}.md` | Q33–Q38 | `limitations`, `communication_prefs`, `work_context` |
| **6** | Goals & Priorities | `06-goals-and-priorities{suffix}.md` | Q39–Q44 | `growth_goals`, `work_context` |
| **7** | Personal Context | `07-personal-context{suffix}.md` | Q45–Q50 | `work_context`, `communication_prefs`, `limitations` |

*Suffix rule:* English files have no suffix (`.md`); Arabic files use `_MSA.md` within `questions/AR-MSA/`.

### 3.4 Markdown Parsing Engine
The parser reads each category markdown file and extracts question blocks matching:
- **ID & Title:** `## Q(\d+):\s*(.+)`
- **Verbatim Question:** Lines beginning with `**Question:**\s*(.+)` or localized Arabic equivalent `**السؤال:**\s*(.+)`.

If question lines wrap across multiple lines, concatenate them cleanly into a single prompt string.

### 3.5 Core Engine API Functions
The module exposes the following clean public interfaces:

1. `load_category_questions(category_id: int, lang: str = "en") -> list[Question]`  
   Loads and parses questions for a specific category.
2. `load_all_questions(lang: str = "en") -> dict[str, Question]`  
   Loads all 50 questions keyed by ID (`"Q01"` to `"Q50"`). Caches results in memory for the process lifetime.
3. `get_question_pair(pair_index: int, lang: str = "en") -> list[Question]`  
   Returns the 2 questions for turn `pair_index` (where `pair_index` is `0` to `24`).  
   - Index `0` returns `[Q01, Q02]`.  
   - Index `24` returns `[Q49, Q50]`.  
   - Raises `IndexError` or returns empty list for indices $\ge 25$.

---

## 4. Test Suite Requirements (`test_questions.py`)

A comprehensive standard `unittest` test suite must validate:

1. **Complete English Ingestion:**
   - Assert `len(load_all_questions("en")) == 50`.
   - Verify every ID from `Q01` through `Q50` exists.
   - Assert prompt strings are non-empty and stripped of markdown formatting artifacts.
2. **Complete Arabic Ingestion:**
   - Assert `len(load_all_questions("ar")) == 50`.
   - Verify every ID from `Q01` through `Q50` exists.
3. **Turn Pairing & Sequence Validation:**
   - Verify turn `0` returns `Q01` and `Q02`.
   - Verify turn `24` returns `Q49` and `Q50`.
   - Verify out-of-range turn indices handle boundaries gracefully.
4. **Environment Override:**
   - Verify setting `MYSPEC_QUESTIONS_PATH` to a custom temporary directory correctly overrides path resolution.

---

## 5. Acceptance Criteria & Definition of Done

* [ ] `questions.py` is implemented with zero external third-party dependencies (stdlib only).
* [ ] Markdown parsing correctly handles both `EN` and `AR-MSA` files.
* [ ] Category and target module mappings match `master_interview_architecture.md` exactly.
* [ ] `test_questions.py` executes and passes 100% of test cases.
* [ ] Existing project files remain completely untouched and unmodified.
