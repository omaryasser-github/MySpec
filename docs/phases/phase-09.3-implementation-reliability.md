# Phase 9.3: Implementation Reliability

## 1. Objective

Harden the local MCP server codebase (`mcp-server/src/myspec_mcp_server/profile.py`) against runtime edge cases, regex keyword collisions, and markdown parsing flaws when reading user-provided profiles, backed by a comprehensive unit test suite.

---

## 2. Scope & Issues Addressed

* **Issue F (Parser & Matcher Edge Cases in `profile.py`):**
  1. **Substring keyword collisions:** `find_technology_terms` matches both compound terms (e.g., `react native`) and constituent terms (e.g., `react`), creating duplicate/skewed mentions in gap analysis.
  2. **Code comment contamination:** `_markdown_sections` identifies any line starting with `#` as a section title, erroneously splitting code snippets containing Python/Bash comments (e.g., `# comment`) into fake sections.
  3. **Empty header truncation:** When top-level headers (e.g., `# Developer Profile`) are immediately followed by subheadings (`## Skills`), the top header is silently dropped without saving.
  4. **Unbounded minute allocation:** `allocate_minutes` assumes valid positive input without internal lower-bound guards.

---

## 3. Key Tasks & Subtasks

### Task 1: Refactor Technology Term Matching (`find_technology_terms`)
* Order terms by descending length (longest match first).
* Implement span-aware or token-safe boundary matching to prevent constituent terms from matching inside already claimed spans (e.g., if `react native` matches, suppress the inner `react` match unless distinct).
* Ensure deduplicated, normalized output.

### Task 2: Harden Markdown Section Parser (`_markdown_sections`)
* Introduce a fenced code block state tracker (`in_code_block: bool`).
* Ignore `#` lines that occur within code fences (```` ``` ````) to preserve code comments as body text.
* Fix header stack handling so that parent headers without immediate body text are preserved or properly associated with their child sections rather than dropped.

### Task 3: Internal Guardrails on Helper Functions
* Add validation in `allocate_minutes(total: int)` to enforce `total >= 5`, falling back gracefully to sensible distribution if invoked below minimum.
* Enhance error details in profile snapshot reporting when encountering unusual file encodings or corrupt formats.

### Task 4: Expand MCP Unit Test Suite (`tests/test_profile.py` & `tests/test_server.py`)
* Add test case: Markdown profile containing Python code blocks with `#` comments to verify sections remain intact.
* Add test case: Input text containing `"React Native"` verifying clean lexical matching without spurious duplicate sub-tokens.
* Add test case: Markdown containing immediate nested headings (`# Title\n## Subtitle`).
* Add test case: Edge input for session minute allocation.

---

## 4. Expected Outcome / Definition of Done

1. `find_technology_terms` produces clean, collision-free matches on compound technology names.
2. `_markdown_sections` safely parses markdown profiles containing code snippets and nested headers without corrupting section titles or losing content.
3. All existing and new unit tests in `mcp-server/tests/` pass with 100% success.
4. No network dependencies or extra third-party libraries introduced.

---

## 5. Constraints & Dependencies

* Must preserve existing zero-network, local-only stdio design.
* Must maintain compatibility with Python 3.10+.
