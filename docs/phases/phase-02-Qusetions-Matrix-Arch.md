# 📝 Phase 2: Questions Matrix Architecture, File Separation & Localization


## Category Separation Architecture:

- **Separated the 50 structured questions across 7 distinct Markdown files** (`01-identity.md` through `07-growth-goals.md`) inside the `/questions` directory rather than lumping them into a single monolithic document.

## Architectural Rationale:

- **Modular maintenance:** Allows isolated updates, translations, or community PRs for a single category without touching the rest of the question matrix.

- **Direct alignment with future local Model Context Protocol (MCP) servers:** Prepares the filesystem for granular reading operations, avoiding heavy parsing overhead when isolating specific persona categories.

## Question Sourcing & Categorization:

- **Curated 50 targeted developer questions** across 7 comprehensive domains: Basic Identity, Current Skills & Tech Stack, In-Progress Learning, Known Technical Limitations, Communication & Output Preferences, Work Context, and Long-Term Growth Goals.

- **Curated from established prompt-engineering frameworks** to capture granular technical capability without triggering fatigue.

## Localization Strategy & Language Scoping:

- **English Version:** Formulated the primary standard technical questionnaire tailored for global developer workflows.

- **Arabic MSA Version (ar-msa):** Developed a complete Modern Standard Arabic translation to serve regional developers while maintaining clear, professional technical terminology.

- **Egyptian Arabic Exclusion (ar-eg):** Explicitly decided to drop the dialectal Egyptian Arabic version after initial evaluation. Dialectal variations introduce unnecessary maintenance overhead, risk ambiguous AI interpretation, and lack the standardization required for accurate persona parsing across global LLMs.