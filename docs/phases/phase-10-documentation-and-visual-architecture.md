# Phase 10: Documentation Harmonization & Visual Architecture

## 1. Objective

Upgrade and harmonize the project's primary entry-point documentation—[`README.md`](../../README.md) and [`docs/how-it-works.md`](../how-it-works.md)—to accurately represent the completed Phase 9 architecture, featuring clean, precise, and easily digestible Mermaid diagrams for both system architecture and lifecycle sequence workflows.

---

## 2. Scope & Target Files

* **`README.md`**:
  * Add a dedicated visual architecture section with two clean, readable Mermaid diagrams:
    1. **System Architecture Overview:** Minimal block diagram illustrating how Web LLMs, local storage, the MCP server, and AI IDE hosts interconnect.
    2. **System Sequence Diagram:** Step-by-step workflow tracking the user, Web LLM, local disk (`~/.myspec/`), MCP server, and AI host across the 4 stages of the MySpec lifecycle.
  * Harmonize feature descriptions and quick-start instructions to reflect standalone prompt execution and dual `.md` / `.json` profile discovery.
* **`docs/how-it-works.md`**:
  * Replace the legacy ASCII box diagram with a modern, clear Mermaid architecture flowchart.
  * Update profile storage references to document the dual `profile.md` / `profile.json` discovery capability implemented in Phase 9.1.
  * Align the `profile_update.md` section with the formal Semantic Versioning and RFC 6902 JSON Patch specifications completed in Phase 9.2.

---

## 3. Implementation Details

### Task 1: Documenting System Architecture & Sequence in `README.md`
* Introduce `## 🏗️ System Architecture & Workflow` right after Features.
* Craft Diagram 1 with focused, non-cluttered boxes:
  * Profile Creation (`master-interview.md` $\rightarrow$ Web LLM)
  * Local Storage (`~/.myspec/profile.json` or `profile.md`)
  * Local MCP Server (stdio, read-only resources & tools)
  * AI Host / IDE (Cursor, Claude Desktop, Windsurf)
  * Post-Project Evolution (`profile_update.md`)
* Craft Diagram 2 with a clean sequence flow showing:
  1. Discovery Interview in Web Chat.
  2. Saving profile locally.
  3. MCP auto-discovery by Host IDE.
  4. Project onboarding with PRD & gap analysis.
  5. Shipped delivery evidence leading to verified profile update.

### Task 2: Modernizing `docs/how-it-works.md`
* Replace lines 15–45 (ASCII box diagram) with a clean, semantic Mermaid diagram.
* Update table entries and text to reflect dual `.json` (machine SSOT) and `.md` (human companion) profile persistence.
* Document the RFC 6902 JSON Patch and 5-level Implementation Depth Rubric in the profile update section.

---

## 4. Expected Outcome / Definition of Done

1. `README.md` provides an immediate visual understanding of the complete MySpec ecosystem without ambiguity.
2. Both Mermaid diagrams render cleanly, remain concise and uncluttered, and strictly reflect actual implementation.
3. `docs/how-it-works.md` is technically accurate, has no outdated ASCII sketches, and accounts for all Phase 9 system capabilities.
