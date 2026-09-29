# Phase 9.4: Repository Cleanup & Naming Consistency

## 1. Objective

Standardize file taxonomy and eliminate shell hazards, typographical errors, and inconsistent casing across filenames, prompt regexes, and documentation links.

---

## 2. Scope & Issues Addressed

* **Issue G (Naming Conventions & Shell Hazards):**
  1. Reserved shell characters (`&`) in filenames: `03-knowledge-&-skill.md`, `04-tools-&-workflow.md`, `06-gools-&-priorities.md`.
  2. Typos in filenames and regexes: `gools` instead of `goals`, `phase-02-Qusetions...` instead of `phase-02-questions...`.
  3. Casing inconsistencies: `05-Decision-make.md` (uppercase `D`, verb form) vs lower kebab-case.
  4. Outdated cross-references across `prompts/master-interview.md`, `docs/how-it-works.md`, and phase documents.

---

## 3. Key Tasks & Subtasks

### Task 1: Normalize Question Bank Filenames
* Adopt strict, POSIX-compliant kebab-case across all question files:
  * Rename English files:
    * `03-knowledge-&-skill.md` $\rightarrow$ `03-knowledge-and-skills.md`
    * `04-tools-&-workflow.md` $\rightarrow$ `04-tools-and-workflows.md`
    * `05-Decision-make.md` $\rightarrow$ `05-decision-making.md`
    * `06-gools-&-priorities.md` $\rightarrow$ `06-goals-and-priorities.md`
  * Rename Arabic (MSA) files accordingly:
    * `03-knowledge-&-skill_MSA.md` $\rightarrow$ `03-knowledge-and-skills_MSA.md`
    * `04-tools-&-workflow_MSA.md` $\rightarrow$ `04-tools-and-workflows_MSA.md`
    * `05-Decision-make_MSA.md` $\rightarrow$ `05-decision-making_MSA.md`
    * `06-gools-&-priorities_MSA.md` $\rightarrow$ `06-goals-and-priorities_MSA.md`

### Task 2: Standardize Documentation Filenames
* Rename inconsistent phase files:
  * `Phase-01-Project-Foundation.md` $\rightarrow$ `phase-01-project-foundation.md`
  * `phase-02-Qusetions-Matrix-Arch.md` $\rightarrow$ `phase-02-questions-matrix-arch.md`

### Task 3: Update Global References Across Code & Prompts
* Update `master-interview.md` (lines 140–152) to point to the corrected filenames and remove the hardcoded `gools` typo pattern.
* Update file tables and markdown links in `docs/how-it-works.md`, `README.md`, and all phase records.
* Ensure all internal links resolve accurately on case-sensitive filesystems.

---

## 4. Expected Outcome / Definition of Done

1. Zero shell-hazard characters (`&`, spaces, special symbols) in repository filenames.
2. Typos eliminated from all paths, filenames, and prompt reference blocks.
3. Fully uniform lowercase kebab-case across all documentation and matrix files.
4. All markdown links and path references across the repository validate without broken targets.

---

## 5. Constraints & Dependencies

* Must coordinate path renames with Phase 9.1 so that the standalone prompt distribution and question bank refer to the finalized filenames.
