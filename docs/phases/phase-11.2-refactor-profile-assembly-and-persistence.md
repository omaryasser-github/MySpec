# Phase 11.2: Profile Assembly & Atomic Persistence (`profile.py`)

> **Architectural Foundation & Source of Truth:**  
> This specification is derived directly from [`docs/master_interview_architecture.md`](../master_interview_architecture.md), specifically addressing **Q7 (Transforming Answers into Profile Structure)**, **Q8 (Profile Creation & Update Workflow)**, **Q11 (Single Source of Truth for Updates)**, and **Layer 2 (Profile Data Contract & I/O)**.

---

## 1. Objective

Extend `myspec_mcp_server/profile.py` with write-side capabilities to complete the profile lifecycle. Implement `build_profile` to systematically transform raw answer dictionaries into canonical MySpec JSON structures, and implement `save_profile` with atomic filesystem operations to safeguard against corrupted or partially-written profile files.

Crucially, this phase extends `profile.py` while leaving all existing read-side functions (`load_profile`, `extract_skills`, `extract_preferences`, `get_profile_path`, `resource_text`) completely intact.

---

## 2. Scope & Target Files

* **Modify**: `mcp-server/src/myspec_mcp_server/profile.py` (Add `build_profile` and `save_profile`)
* **Modify**: `mcp-server/tests/test_profile.py` (Add unit tests for transformation and persistence)
* **Reference**: `output/output_generation_prompt.md` (Canonical Pydantic schema and module definitions)

---

## 3. Technical Specifications

### 3.1 Profile Schema & Section Grouping Contract
The MySpec profile format defines 7 canonical module keys. When answers are collected, each question ID (`Q01` through `Q50`) is mapped to its corresponding module(s) as defined in the architectural blueprint:

- **Q01–Q10:** $\rightarrow$ `identity` & `work_context`
- **Q11–Q18:** $\rightarrow$ `communication_prefs`
- **Q19–Q25:** $\rightarrow$ `current_skills`, `learning_in_progress`, `limitations`
- **Q26–Q32:** $\rightarrow$ `current_skills`, `work_context`, `limitations`
- **Q33–Q38:** $\rightarrow$ `limitations`, `communication_prefs`, `work_context`
- **Q39–Q44:** $\rightarrow$ `growth_goals`, `work_context`
- **Q45–Q50:** $\rightarrow$ `work_context`, `communication_prefs`, `limitations`

Each module stores question answers keyed by question ID, preserving raw user responses as canonical evidence.

### 3.2 The `build_profile` Function Contract
```python
def build_profile(
    answers: dict[str, str],
    existing_profile: dict | None = None,
    language: str = "en",
) -> dict:
    """Transform collected interview answers into a canonical MySpec profile dict.
    
    Args:
        answers: Mapping of question IDs (e.g. "Q01") to user responses.
        existing_profile: Optional previous profile dictionary for incremental updates.
        language: Language code ("en" or "ar").
        
    Returns:
        Structured dictionary adhering to canonical MySpec profile schema.
    """
```

#### Detailed Transformation Logic:
1. **Metadata & Status Tracking:**
   - Compute answered questions: count entries where `answer` is non-empty and not `"__SKIPPED__"`.
   - Calculate `completion_rate`: `answered_count / 50.0`.
   - Determine `status`: `"complete"` if `completion_rate == 1.0` else `"partial"`.
   - Set top-level metadata:
     ```python
     {
         "schema_version": 1,
         "status": status,
         "completion_rate": completion_rate,
         "updated_at": current_iso_timestamp(),
         "language": language,
         "identity": {},
         "work_context": {},
         "communication_prefs": {},
         "current_skills": {},
         "learning_in_progress": {},
         "limitations": {},
         "growth_goals": {},
         "skipped_fields": []
     }
     ```
2. **Skipped / Declined Questions:**
   - If an answer equals `"__SKIPPED__"` or `"__DECLINED__"`, record the question ID in `skipped_fields`.
3. **Merging Strategy (For Profile Updates):**
   - If `existing_profile` is provided, preserve all existing keys and metadata.
   - Overwrite or add newly supplied question IDs into their respective modules.

### 3.3 The `save_profile` Atomic Write Contract
```python
def save_profile(profile_data: dict, target_path: Path | None = None) -> Path:
    """Atomically save profile data to disk in JSON format.
    
    Args:
        profile_data: The profile dictionary to persist.
        target_path: Optional destination path; defaults to get_profile_path().
        
    Returns:
        Path to the saved profile.json.
    """
```

#### Atomic Persistence Algorithm:
To guarantee zero file corruption on crash or mid-write power loss:
1. Determine `destination_path`:
   - If `target_path` is provided, use it.
   - Otherwise, resolve using `get_profile_path()`. If the resolved path ends in `.md`, default write destination to sibling `profile.json` (machine SSOT).
2. Ensure destination directory exists:
   ```python
   destination_path.parent.mkdir(parents=True, exist_ok=True)
   ```
3. Write to a temporary file in the same directory:
   ```python
   temp_path = destination_path.with_suffix(".json.tmp")
   temp_path.write_text(
       json.dumps(profile_data, indent=2, ensure_ascii=False),
       encoding="utf-8"
   )
   ```
4. Atomically replace the destination file:
   ```python
   temp_path.replace(destination_path)
   ```

---

## 4. Test Suite Requirements (`test_profile.py`)

Extend `mcp-server/tests/test_profile.py` with tests verifying:

1. **Full Profile Build:**
   - Supply a mock dictionary with 50 answers (`Q01` to `Q50`).
   - Assert `completion_rate == 1.0` and `status == "complete"`.
   - Verify all 7 module dictionaries are populated with expected question IDs.
2. **Partial Profile & Skipped Fields:**
   - Supply 30 answers with 5 `"__SKIPPED__"` entries.
   - Assert `completion_rate == 0.5` (25/50) and `status == "partial"`.
   - Assert `skipped_fields` contains the 5 skipped question IDs.
3. **Atomic File Write & Directory Creation:**
   - Use `tempfile.TemporaryDirectory` with a non-existent nested subdirectory.
   - Assert `save_profile` creates the parent directory and successfully writes `profile.json`.
   - Verify temporary file `.json.tmp` is completely removed after the atomic rename.
4. **Immediate Read-Back Round-Trip:**
   - Call `save_profile(built_data, temp_profile_path)`.
   - Immediately call existing `load_profile(temp_profile_path)`.
   - Assert `snapshot.status == "json"` and `snapshot.profile["completion_rate"] == 1.0`.

---

## 5. Acceptance Criteria & Definition of Done

* [ ] `build_profile` accurately maps question responses across all 7 MySpec modules.
* [ ] Incremental update merge preserves existing profile data.
* [ ] `save_profile` uses atomic temporary file replacement.
* [ ] All existing functions in `profile.py` continue to behave identically.
* [ ] All new tests pass alongside all existing tests in `test_profile.py`.
