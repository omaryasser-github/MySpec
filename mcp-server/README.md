# MySpec Local MCP Server

The MySpec MCP server exposes a user's local profile to an existing MCP-capable AI host. The host launches this package as a child process and acts as the MCP client; this repository does not include a separate client application.

The server uses **stdio only**. It reads the canonical `~/.myspec/profile.json` on demand and saves confirmed profiles to canonical JSON via `finalize_interview`. It provides no authentication, ports, HTTP transport, cloud service, database, telemetry, update check, or network call.

## Requirements

- Python 3.10 or newer.
- Cursor, Claude Desktop, Windsurf, or another MCP host that supports stdio servers.
- A local canonical profile at `~/.myspec/profile.json` (or a path resolved via CLI, `MYSPEC_PROFILE_PATH`, or `~/.myspec/config.json`).

## Local installation

From this directory, create a virtual environment, activate it, and install the package:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

On macOS/Linux, activate with `source .venv/bin/activate`. The install retrieves the pinned MCP SDK and Pydantic dependencies; after installation, server runtime uses local profile I/O and stdio only.

## Path Precedence & Configuration

The server resolves the canonical profile using deterministic precedence:

1. **CLI Argument:** `--profile <path>` passed to `myspec-mcp-server`.
2. **Environment Variable:** `MYSPEC_PROFILE_PATH`.
3. **MySpec Configuration File:** `profile_path` key in `~/.myspec/config.json`.
4. **Default:** `~/.myspec/profile.json`.

All selected paths must end with `.json`. If a selected path uses `.md`, the server rejects it and prompts you to run migration.

### Legacy Markdown Migration

If you have an existing legacy `profile.md`, migrate it to canonical `profile.json` with the migration command:

```powershell
myspec-mcp-server migrate
# Or specify explicit paths:
myspec-mcp-server migrate --source ~/.myspec/profile.md --dest ~/.myspec/profile.json
```

Migration parses legacy Markdown, validates it against the canonical Pydantic model, creates a safe `.bak` archive copy of your original file, and atomically writes `profile.json`. Migration never overwrites an existing JSON profile.

## Host configuration

Use the host's existing MCP server configuration and insert an entry like this, replacing paths with absolute paths on the user's machine:

```json
{
  "mcpServers": {
    "myspec-local": {
      "command": "C:/path/to/MySpec/mcp-server/.venv/Scripts/myspec-mcp-server.exe",
      "args": ["--profile", "C:/Users/your-name/.myspec/profile.json"],
      "env": {
        "MYSPEC_LANG": "en"
      }
    }
  }
}
```

On macOS/Linux, use the executable at `.venv/bin/myspec-mcp-server`. `args` and `MYSPEC_PROFILE_PATH` are optional; without them, the server defaults to `~/.myspec/profile.json`. `MYSPEC_LANG` accepts `en`/`english` or `ar`/`msa`/`ar-MSA`; unsupported values fall back to English.

The host starts and stops the server process. To check package startup manually, run `myspec-mcp-server` from the activated environment; it waits for MCP messages on stdin and stdout. Do not use the command as a regular terminal UI.

## Exposed MCP surface

### Resources

- `myprofile://summary` — concise profile context.
- `myprofile://skills` — skills, learning areas, and skill-related limitations.
- `myprofile://preferences` — communication and output preferences.
- `myprofile://full` — full local profile text.

### Tools

- `start_interview(language=None)` — starts an interactive MySpec interview session, returning Question Pair 0.
- `advance_interview(pair_index, answers_so_far, language=None)` — submits answers and returns the next pair or signals completion (requires non-empty answers or explicit disposition sentinels).
- `finalize_interview(answers, language=None, output_preference="english_only")` — builds, validates with Pydantic, and atomically persists canonical `profile.json`.
- `get_gap_analysis(project_description)` — returns local skill evidence and explicit technology-term overlap to support host-side gap reasoning. A text match is not a proficiency claim.
- `get_onboarding_plan(topic, minutes=60)` — returns a time-boxed learning agenda informed by the local skill view.

### Prompts

- `onboarding(project_description)` — prepares a project onboarding request with the full local profile context.
- `gap_check(project_description)` — prepares a focused gap analysis with profile evidence and local lexical matches.

The server reads the profile afresh on each call. Missing, unreadable, empty, malformed, or migration-required states are reported gracefully in resource/tool results; they do not crash the server process.

## Configuration Reference

| Setting | Default | Purpose |
| --- | --- | --- |
| `--profile <path>` | (None) | CLI override for canonical `profile.json` path. |
| `MYSPEC_PROFILE_PATH` | `~/.myspec/profile.json` | Environment override for canonical `profile.json` path. |
| `~/.myspec/config.json` | `{"profile_path": "..."}` | MySpec-owned config file for local profile path. |
| `MYSPEC_QUESTIONS_PATH` | `<package_root>/../../../questions` | Override canonical question bank directory. |
| `MYSPEC_LANG` | `en` | Select English or Modern Standard Arabic response labels. |

The local OS process and filesystem permissions are the trust boundary.

## Tests

From this directory, run:

```powershell
python -m unittest discover -s tests -v
```

Tests cover canonical JSON loading, path precedence, configuration parsing, atomic file persistence, legacy Markdown migration, question bank parity and caching, resource/tool/prompt registration, and launching the server as a stdio child process.

