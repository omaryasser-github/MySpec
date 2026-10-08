# MySpec Architecture Design — Master Interview & Core Integration
## Senior Engineer Feedback (No Changes — Analysis Only)

---

## Big Picture First: The Target Architecture in One Diagram

```
USER types: /master-interview start
           │
           ▼
┌──────────────────────────────────────────────────────────┐
│              MCP Server (server.py)                       │
│  Tool: start_interview()                                  │
│    → reads MYSPEC_LANG from env                           │
│    → calls questions.py: load_category(lang, 1)           │
│    → returns pair [Q01, Q02] + session state token       │
└──────────────┬───────────────────────────────────────────┘
               │ (host model presents questions to user)
               ▼
         User answers Q01 & Q02
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  Tool: advance_interview(state_token, answers)            │
│    → loads next pair from questions.py                    │
│    → updates accumulated answers dict                     │
│    → returns next pair OR "interview_complete"            │
└──────────────┬───────────────────────────────────────────┘
               │ (repeats 25 times for 50 questions)
               ▼
        All 50 questions answered
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│  Tool: finalize_interview(state_token)                    │
│    → calls profile.py: build_profile(answers)             │
│    → calls profile.py: save_profile(profile_data, path)   │
│    → returns {status: "saved", path: "~/.myspec/..."}     │
└──────────────┬───────────────────────────────────────────┘
               │
               ▼
       ~/.myspec/profile.json  ← written to disk
               │
               ▼
┌──────────────────────────────────────────────────────────┐
│         MySpec Core (existing server.py surfaces)         │
│  myprofile://skills  myprofile://summary                  │
│  get_gap_analysis()  get_onboarding_plan()                │
│  onboarding()        gap_check()                          │
└──────────────────────────────────────────────────────────┘
```

---

## Q1 — How Do I Make `questions/` the Single Source of Truth?

**Current problem:** The 50 questions exist in THREE places simultaneously:
1. `questions/EN/` — 7 Markdown files (the intended source of truth)
2. `questions/AR-MSA/` — 7 Arabic Markdown files
3. `prompts/master-interview.md` lines 137–420 — the **entire bank re-embedded** in `<QUESTIONS_BANK>`

This means if you edit Q03 in `questions/EN/03-knowledge-and-skills.md`, the copy in `master-interview.md` is now stale. You have two independent sources of truth drifting apart over time.

**The fix (conceptually):**

Create a new Python module `questions.py` inside `myspec_mcp_server/` that:
1. Knows the absolute path to the `questions/` directory (relative to the package).
2. Parses the Markdown files to extract each `## QXX: Title` + `**Question:**` line.
3. Returns structured question objects: `{id, title, text_en, text_ar, context, category}`.

The `questions/` directory then becomes the **only** place questions live. `master-interview.md` stops embedding the full bank and instead references the workflow rules only.

**Key design principle:** Parse the Markdown files at load time (or cache them). Never hardcode question text in Python. The files ARE the database.

---

## Q2 — How Do I Refactor `master-interview.md` So It Defines Workflow, Not Questions?

**Current state:** `master-interview.md` is 505 lines because it contains:
- Lines 1–136: The state machine, operating principles, examples (KEEP THESE)
- Lines 137–504: The entire `<QUESTIONS_BANK>` with all 50 questions embedded (REMOVE THIS)

**The refactoring target:**

`master-interview.md` should be ~120–140 lines containing only:
- The **Role and Purpose** section
- The **Operating Principles** section
- The **State Machine** (States 0–7)
- The **Category-to-Profile module mapping** table (lines 127–135 — critical, keep it)
- The **Off-topic and Omission handling** rules
- The **Few-shot examples**

The `<QUESTIONS_BANK>` section is fully deleted. Instead, `master-interview.md` says:

```
## Question Bank
Questions are loaded dynamically from questions/ by the MCP server.
The MCP host receives exactly two questions per turn via the advance_interview tool.
```

This way `master-interview.md` becomes an **orchestration specification**, not a data file.

**For the web LLM use case (backwards compatibility):** Keep a separate `prompts/master-interview-standalone.md` that remains self-contained with the embedded bank. This is for users who still want to paste it into ChatGPT/Claude. This separation was already discussed in Phase 9.1 Issue A.

---

## Q3 — How Do I Make `/master-interview start` Behave as a Real Workflow?

The `/master-interview` command is what the user types in the AI host (Cursor, Claude Desktop, etc.). The host model sees this and needs to call MCP tools.

**The flow:**

1. User types `/master-interview start`.
2. The host AI calls MCP tool `start_interview()`.
3. `start_interview()` returns the first question pair + a session state token.
4. The host AI presents the questions to the user.
5. User answers → host AI calls `advance_interview(token, {"Q01": "...", "Q02": "..."})`.
6. Repeat until `advance_interview` returns `{"status": "complete"}`.
7. Host AI calls `finalize_interview(token)`.
8. `profile.json` is written, success message returned.

**What the `start_interview` tool must return:**

```json
{
  "session_token": "uuid-or-hash",
  "state": "S1",
  "active_category": 1,
  "category_name": "Identity and Work",
  "pair_index": 0,
  "questions": [
    {"id": "Q01", "text": "What is your current role..."},
    {"id": "Q02", "text": "What industry vertical..."}
  ],
  "total_questions": 50,
  "answered_count": 0
}
```

**Important:** The session token is how state is maintained across turns. Because the MCP server is stateless (no in-memory session), the token encodes the state. This is explained in Q6 below.

---

## Q4 — How Should the MCP Server Internally Load `master-interview.md` and Questions?

**Two separate responsibilities:**

**A. `master-interview.md` (the workflow specification):**
The MCP server does NOT need to load or parse `master-interview.md` at all. The state machine it describes is reimplemented as Python logic inside `questions.py` and the interview tools. The `.md` file is documentation for humans and the web LLM use case. The server implements the same rules in code.

**B. `questions/` (the data):**
The server loads question files via a `questions.py` module. The path resolution:

```
MYSPEC_QUESTIONS_PATH (env override, optional)
    → falls back to: <package_root>/../../questions/{lang}/*.md
    → or relative to an installed data path
```

**The cleanest approach for this project's structure:** Since the MCP server lives at `mcp-server/` and `questions/` is at the repo root, use `MYSPEC_QUESTIONS_PATH` as an environment variable override (same pattern as `MYSPEC_PROFILE_PATH`). The default resolves relative to the repo root.

This keeps the zero-network, local-only design intact and follows the exact same env-override pattern you already use.

---

## Q5 — How Should the Interview Select Language and Category Files?

**Language selection** already works — `get_language()` in `profile.py` reads `MYSPEC_LANG` and returns `"en"` or `"ar"`. Reuse this exactly as-is.

**File selection logic** (in new `questions.py`):

```
language = get_language()          # "en" or "ar"
lang_dir = "EN" if lang=="en" else "AR-MSA"
suffix   = "" if lang=="en" else "_MSA"

files = {
  1: f"01-identity-work{suffix}.md",
  2: f"02-communication-style{suffix}.md",
  3: f"03-knowledge-and-skills{suffix}.md",
  4: f"04-tools-and-workflows{suffix}.md",
  5: f"05-decision-making{suffix}.md",
  6: f"06-goals-and-priorities{suffix}.md",
  7: f"07-personal-context{suffix}.md",
}
path = questions_root / lang_dir / files[category_number]
```

**Category ranges** (already defined in `master-interview.md`, just replicate in Python):

| Category | ID Range | Profile Modules |
|:---|:---|:---|
| 1 Identity & Work | Q01–Q10 | `identity`, `work_context` |
| 2 Communication Style | Q11–Q18 | `communication_prefs` |
| 3 Knowledge & Skills | Q19–Q25 | `current_skills`, `learning_in_progress`, `limitations` |
| 4 Tools & Workflow | Q26–Q32 | `current_skills`, `work_context`, `limitations` |
| 5 Decision-Making | Q33–Q38 | `limitations`, `communication_prefs`, `work_context` |
| 6 Goals & Priorities | Q39–Q44 | `growth_goals`, `work_context` |
| 7 Personal Context | Q45–Q50 | `work_context`, `communication_prefs`, `limitations` |

This table already exists in `master-interview.md` lines 127–135. It becomes a Python constant in `questions.py`.

---

## Q6 — How Should User Answers Be Collected and Mapped to Question IDs?

**The state problem:** MCP tools are stateless — each tool call is independent. You cannot store answers in memory between calls. 

**The solution: client-side state accumulation.**

The host model (Claude Desktop, Cursor, etc.) maintains the accumulated answer dictionary across turns. Each `advance_interview` call receives the FULL answers collected so far, not just the latest pair:

```json
Tool call: advance_interview({
  "current_pair_index": 3,
  "answers_so_far": {
    "Q01": "Senior backend engineer at a SaaS company...",
    "Q02": "B2B SaaS, SME market...",
    "Q03": "7 years...",
    "Q04": "Team of 5..."
  },
  "language": "en"
})
```

This is the standard MCP/LLM pattern — the client accumulates state, the server is stateless. It mirrors exactly how your existing `onboarding` and `gap_check` prompts work: each call is independent and receives full context.

**Answer structure:** Each answer is a `{question_id: answer_text}` dict. Question IDs (`Q01`–`Q50`) are the stable keys — they already exist in the question files as `## QXX:` headers.

**Disposition handling** (unknown/skipped/declined) — record as:
```json
{"Q07": "__SKIPPED__"}
```
This maps to `skipped_fields` in the `MySpecProfile` Pydantic model, which already supports this in `output_generation_prompt.md`.

---

## Q7 — How Should Answers Be Transformed Into the Correct `profile.json` Structure?

The mapping is already documented in `master-interview.md` lines 127–135 and in `output_generation_prompt.md`. The Pydantic schema in `output_generation_prompt.md` defines exactly 7 module keys.

**The transformation function** (in `profile.py` as a new `build_profile(answers)` function):

```
Input:  {"Q01": "text", "Q02": "text", ..., "Q50": "text"}
Output: {"identity": {...}, "current_skills": {...}, ..., "growth_goals": {...}}
```

**The mapping logic (no LLM needed — just categorize by Q range):**

The answers are grouped by the category they belong to, then stored under the appropriate profile module key:

- Q01–Q10 answers → `identity` + `work_context` keys
- Q11–Q18 answers → `communication_prefs` keys
- Q19–Q25 answers → `current_skills`, `learning_in_progress`, `limitations` keys
- Q26–Q32 answers → `current_skills`, `work_context`, `limitations` keys
- Q33–Q38 answers → `limitations`, `communication_prefs`, `work_context` keys
- Q39–Q44 answers → `growth_goals`, `work_context` keys
- Q45–Q50 answers → `work_context`, `communication_prefs`, `limitations` keys

**Important:** The raw answer strings go in as-is under their question ID as the key. The profile stores evidence, not synthesized summaries. The LLM host interprets the evidence — the server just organizes it structurally.

Example final structure:
```json
{
  "schema_version": 1,
  "status": "complete",
  "completion_rate": 1.0,
  "identity": {
    "Q01": "Senior backend engineer at a B2B SaaS company...",
    "Q02": "B2B SaaS, SME market, mid-market customers..."
  },
  "current_skills": {
    "Q19": "Python, FastAPI, PostgreSQL — expert level...",
    "Q26": "Docker, GitHub Actions, VS Code..."
  }
}
```

---

## Q8 — How Should Profile Creation/Update Become Part of the Same Workflow?

**Profile creation** (no existing `profile.json`):
`finalize_interview()` calls `save_profile(profile_data, path)` which writes a new file.

**Profile update** (existing `profile.json` exists):
`start_interview()` checks if a profile already exists via the existing `load_profile()`.
- If it exists: pass `existing_data` into the session state so `build_profile()` can merge.
- The merge strategy: existing fields are preserved, new answers overwrite their specific question IDs.
- This matches the `PREVIOUS_PROFILE` merge contract in `output_generation_prompt.md`.

**The `save_profile()` function** (new, to be added to `profile.py`):
- Takes `data: dict`, `path: Path`.
- Writes atomically: write to `profile.json.tmp`, then `rename()` to `profile.json`.
- Atomic rename prevents corrupt files if the process dies mid-write.
- Validates against the `MySpecProfile` Pydantic schema before writing.
- Returns `{status: "saved", path: str(path)}`.

**Completion rate calculation:**
```python
answered = sum(1 for v in answers.values() if v != "__SKIPPED__")
completion_rate = answered / 50
status = "complete" if completion_rate == 1.0 else "partial"
```

---

## Q9 — How Should MySpec Core Consume the Generated `profile.json`?

**No change needed to MySpec Core (existing tools).** This is the key architectural insight.

The existing surfaces in `server.py` already do exactly this:
- They call `load_profile(get_profile_path())` on every request.
- They read whatever is in `~/.myspec/profile.json`.

Once `finalize_interview()` writes `profile.json` to `~/.myspec/`, every existing tool automatically picks it up on the next call. There is no registration, no cache invalidation, no restart. The file-on-disk IS the integration point.

**The flow after interview completion:**
```
finalize_interview() writes ~/.myspec/profile.json
         │
         ▼
User calls get_gap_analysis("Build a Python service")
         │
         ▼
load_profile() reads the newly written file
         │
         ▼
gap_analysis_payload() works against the new profile data
         │
         ▼
Full gap analysis returned — MySpec Core "knows" the new profile
```

Zero changes to `server.py` resources or tools for Core to work with a freshly created profile.

---

## Q10 — How Should the Master Interview and MySpec Core Be Connected Without Becoming Two Separate Systems?

**The connection is the file.** This is intentional and correct.

```
[Interview Workflow]  →  writes profile.json  →  [MySpec Core reads it]
```

They are NOT two profile management systems. They are two phases of one system:
1. **Phase 1 (Interview):** Creates/updates `profile.json` from user answers.
2. **Phase 2 (Core):** Reads `profile.json` to provide analysis, gap detection, and onboarding.

The only shared code between them is `profile.py` — which is exactly right:
- `load_profile()` is shared (read path, used by Core).
- `save_profile()` is new (write path, used only by Interview finalization).
- `build_profile()` is new (transformation, used only by Interview finalization).
- `get_profile_path()` is shared (path resolution, used by both).

**The architectural boundary:**
```
questions.py    → Interview only (loads question bank)
profile.py      → Both (load_profile for Core, save_profile for Interview)
server.py       → Both (interview tools + core tools, all in same server)
```

One server, one profile file, one `profile.py` module. That's the whole system.

---

## Q11 — How Do I Ensure One Source of Truth and Prevent Conflicting Update Mechanisms?

**Three rules to enforce:**

**Rule 1: Only `profile.py` writes to `profile.json`.**
The write function `save_profile()` lives in `profile.py`. No other module writes profiles. `server.py` tools call `profile.py` functions only.

**Rule 2: Profile updates only happen through finalize_interview or the profile_update workflow.**
The existing `profile_update.md` prompt (SemVer, RFC 6902 JSON Patch) is the approved update path post-project. The interview is the approved creation path. Nothing else writes to the file.

**Rule 3: `questions/` is the only place questions live.**
Remove the `<QUESTIONS_BANK>` from `master-interview.md`. Any question change happens in `questions/EN/` or `questions/AR-MSA/` only. `questions.py` parses them. `master-interview-standalone.md` is generated/synced from them (or updated manually when questions change).

**Anti-patterns to explicitly avoid:**
- ❌ A separate "profile manager" class or module that duplicates `load_profile` / `save_profile`.
- ❌ Storing answers in an MCP resource (resources are read-only by design).
- ❌ A new database or persistent session store (stay file-only).
- ❌ Embedding questions in server.py or questions.py as hardcoded strings.

---

## Q12 — Which Existing MCP Tools/Functions Need to Change?

**Nothing existing changes behavior.** You are adding new surfaces, not modifying existing ones.

| Item | Change Type | What Changes |
|:---|:---|:---|
| `server.py` | **ADD** | 3 new tools: `start_interview`, `advance_interview`, `finalize_interview` |
| `profile.py` | **ADD** | 2 new functions: `build_profile(answers)`, `save_profile(data, path)` |
| New `questions.py` | **CREATE** | New module: question file parser and bank loader |
| `master-interview.md` | **REFACTOR** | Remove `<QUESTIONS_BANK>` block (~380 lines) |
| New `master-interview-standalone.md` | **CREATE** | Self-contained version for web LLM use |
| `pyproject.toml` | **ADD** | `pydantic>=2` as a dependency (for profile validation) |
| Existing tools | **NO CHANGE** | `get_gap_analysis`, `get_onboarding_plan`, `onboarding`, `gap_check` unchanged |
| Existing resources | **NO CHANGE** | All 4 `myprofile://` resources unchanged |
| `profile.py` existing functions | **NO CHANGE** | `load_profile`, `extract_skills`, `get_profile_path`, etc. unchanged |

**The only behavioral change to existing code:** The existing `load_profile()` will now sometimes find a `profile.json` that was written by `finalize_interview()` instead of manually by the user — but it handles this identically since it already reads JSON profiles.

---

## Q13 — What Should Each Layer Be Responsible For?

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: questions.py  (NEW)                                    │
│  Responsibility: Question bank loader                            │
│  - Parse questions/EN/*.md and questions/AR-MSA/*.md            │
│  - Return structured {id, text, category, profile_modules} dicts│
│  - Resolve questions root path (env override or repo-relative)   │
│  - Zero business logic — data loading only                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2: profile.py  (EXTEND — add 2 functions)                 │
│  Responsibility: Profile data contract and I/O                   │
│  Existing: load_profile, extract_*, get_profile_path, resource_text│
│  New:      build_profile(answers) → dict                        │
│            save_profile(data, path) → None (atomic write)       │
│  - All profile schema knowledge lives here                       │
│  - All profile file I/O lives here (both read and write)         │
│  - ProfileSnapshot remains the read-side data object             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: server.py  (EXTEND — add 3 tools)                      │
│  Responsibility: MCP transport and input validation              │
│  Existing: 4 resources, 2 tools, 2 prompts (no changes)         │
│  New tools:                                                       │
│    start_interview(language?)                                    │
│      - Validates inputs, calls questions.py + returns Q01/Q02   │
│    advance_interview(pair_index, answers_so_far, language?)      │
│      - Validates inputs, returns next pair or complete signal    │
│    finalize_interview(answers, output_preference?)               │
│      - Validates completion, calls build_profile + save_profile  │
│  - No business logic here — only validate inputs, delegate, return│
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4: master-interview.md  (DOCUMENT — not code)             │
│  Responsibility: Workflow specification for human + web LLM use  │
│  - State machine rules (States 0–7)                              │
│  - Operating principles                                           │
│  - Category-to-profile mapping table                             │
│  - Few-shot examples                                             │
│  - NO question text (that's questions/ territory)                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  LAYER 5: questions/ directory  (DATA — single source of truth)  │
│  Responsibility: Canonical question bank                         │
│  - 7 EN Markdown files (Q01–Q50)                                │
│  - 7 AR-MSA Markdown files (Q01–Q50)                            │
│  - Parsed by questions.py, never duplicated elsewhere            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Final Summary: What You Are Building vs. What Already Exists

| Already Built (Don't Touch) | To Build (Additive Only) |
|:---|:---|
| `load_profile()` — reads profile | `save_profile()` — writes profile |
| `extract_skills/preferences()` | `build_profile(answers)` — transforms answers |
| `get_profile_path()` | `questions.py` — question bank loader |
| `get_language()` | `start_interview()` MCP tool |
| `gap_analysis_payload()` | `advance_interview()` MCP tool |
| All 4 resources | `finalize_interview()` MCP tool |
| `get_gap_analysis` tool | Refactored `master-interview.md` (orchestration only) |
| `get_onboarding_plan` tool | `master-interview-standalone.md` (web LLM version) |
| `onboarding` / `gap_check` prompts | `pydantic` dependency in `pyproject.toml` |

**Total new code estimate:** ~200–250 lines across `questions.py` (parser) + 3 additions to `profile.py` (build + save + helper) + 3 new tools in `server.py`. No existing code modified.
