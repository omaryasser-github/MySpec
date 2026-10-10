# Phase 11.3: MCP Tool Surface & Stateless State Machine (`server.py`)

> **Architectural Foundation & Source of Truth:**  
> This specification is derived directly from [`docs/master_interview_architecture.md`](../master_interview_architecture.md), specifically addressing **Q3 (Interactive Workflow & Triggering)**, **Q6 (Answer Collection & Stateless State Machine)**, **Q9 (Core Consumption of Generated Profiles)**, **Q12 (Affected MCP Tools & Functions)**, and **Layer 3 (MCP Transport & Input Validation)**.

---

## 1. Objective

Integrate the question engine (Phase 11.1) and profile assembly system (Phase 11.2) into the MCP server transport layer in `mcp-server/src/myspec_mcp_server/server.py`. Expose three clean, standard MCP tools:
1. `start_interview` — initiates the interview and returns the first question pair.
2. `advance_interview` — advances through turn indices and collects accumulated answers.
3. `finalize_interview` — builds and writes the final profile to disk.

Maintain strict **statelessness** across MCP requests by leveraging client-side answer accumulation, and update test assertions to guard against regressions.

---

## 2. Scope & Target Files

* **Modify**: `mcp-server/src/myspec_mcp_server/server.py` (Register 3 new `@mcp.tool()` endpoints)
* **Modify**: `mcp-server/tests/test_server.py` (Update tool registrations test and add end-to-end tool execution tests)
* **Reference**: `mcp-server/src/myspec_mcp_server/questions.py` (From Phase 11.1)
* **Reference**: `mcp-server/src/myspec_mcp_server/profile.py` (From Phase 11.2)

---

## 3. Technical Specifications

### 3.1 The Stateless State Machine Protocol
MCP servers operate via standard stdio JSON-RPC without guaranteed in-memory persistence between calls. As specified in the architecture blueprint, state is preserved via **client-side answer accumulation**:
- Each turn, the AI host maintains `answers_so_far: dict[str, str]`.
- The host passes the turn index and accumulated answers to the server.
- The server validates turn boundaries, fetches questions dynamically from `questions.py`, and returns structured payloads.

### 3.2 Tool 1: `start_interview`
```python
@mcp.tool()
def start_interview(language: str = "en") -> dict:
    """Start an interactive MySpec Master Interview session.
    
    Args:
        language: Language code ("en" or "ar"). Defaults to "en" or MYSPEC_LANG env var.
        
    Returns:
        Structured payload containing initial turn metadata and Question Pair 0 (Q01, Q02).
    """
```
**Payload Contract:**
```json
{
  "pair_index": 0,
  "category_id": 1,
  "category_name": "Identity & Work",
  "questions": [
    {
      "id": "Q01",
      "title": "Current Role and Primary Domain",
      "prompt": "What is your current engineering role and primary technical domain?"
    },
    {
      "id": "Q02",
      "title": "Technical Depth and Experience",
      "prompt": "How many years of professional experience do you have, and in what key stacks?"
    }
  ],
  "total_pairs": 25,
  "total_questions": 50,
  "status": "in_progress"
}
```

### 3.3 Tool 2: `advance_interview`
```python
@mcp.tool()
def advance_interview(
    pair_index: int,
    answers_so_far: dict[str, str],
    language: str = "en"
) -> dict:
    """Advance the interview to the next question pair or signal completion.
    
    Args:
        pair_index: The zero-based index of the completed turn (0 to 24).
        answers_so_far: All question answers accumulated so far (keyed by "Q01", etc.).
        language: Language code ("en" or "ar").
        
    Returns:
        Payload with the next question pair, or {status: "interview_complete", ready_to_finalize: True}.
    """
```
**Progression Logic:**
- If `pair_index < 24`:
  - Calculate `next_index = pair_index + 1`.
  - Fetch questions for `next_index` via `get_question_pair(next_index, language)`.
  - Return `{"pair_index": next_index, "category_name": ..., "questions": [...], "status": "in_progress"}`.
- If `pair_index >= 24`:
  - Return `{"status": "interview_complete", "ready_to_finalize": True, "total_answered": len(answers_so_far)}`.

### 3.4 Tool 3: `finalize_interview`
```python
@mcp.tool()
def finalize_interview(
    answers: dict[str, str],
    language: str = "en"
) -> dict:
    """Build and persist the final MySpec profile from accumulated interview answers.
    
    Args:
        answers: Complete dictionary of question answers (keyed by question ID).
        language: Language code ("en" or "ar").
        
    Returns:
        Confirmation payload with saved path and completion rate.
    """
```
**Execution Sequence:**
1. Check if an existing profile exists via `load_profile()`.
2. Call `build_profile(answers, existing_profile, language)`.
3. Call `save_profile(profile_data)`.
4. Return:
   ```json
   {
     "status": "saved",
     "path": str(saved_path),
     "completion_rate": profile_data["completion_rate"],
     "profile_status": profile_data["status"]
   }
   ```

---

## 4. Test Suite Requirements (`test_server.py`)

### ⚠️ Critical Regression Guard
In `mcp-server/tests/test_server.py` line 58, the test suite currently asserts:
```python
tools = await client.list_tools()
self.assertEqual(
    {tool.name for tool in tools.tools},
    {"get_gap_analysis", "get_onboarding_plan"},
)
```
**This assertion must be updated** to expect the full set of 5 registered tools:
```python
{"get_gap_analysis", "get_onboarding_plan", "start_interview", "advance_interview", "finalize_interview"}
```

### New Integration Tests to Implement:
1. **Tool Listing Verification:**
   - Assert all 5 tools are discovered with proper parameter schemas.
2. **`start_interview` Call Verification:**
   - Call `start_interview` via `client.call_tool()`.
   - Assert returned structured content contains pair index 0, Q01, and Q02.
3. **`advance_interview` Call Verification:**
   - Call `advance_interview` with `pair_index: 0` and mock answers for `Q01`, `Q02`.
   - Assert returned payload contains `pair_index: 1`, Q03, and Q04.
   - Call `advance_interview` with `pair_index: 24` and assert completion signal.
4. **End-to-End Interview Finalization & Core Consumption:**
   - Call `finalize_interview` with mock answers.
   - Assert file is written to the test temporary directory.
   - Call `client.read_resource("myprofile://summary")` and assert MySpec Core immediately reads the new profile without server restart.

---

## 5. Acceptance Criteria & Definition of Done

* [ ] Three new tools (`start_interview`, `advance_interview`, `finalize_interview`) are registered in `server.py`.
* [ ] Tools operate statelessly relying on client-side accumulated answers.
* [ ] `test_server.py` exact-match tool set assertion is updated to include all 5 tools.
* [ ] Full MCP client test suite passes, including `test_stdio_child_process_serves_profile_without_a_custom_client_app`.
* [ ] Existing resources and analysis tools remain 100% backward compatible.
