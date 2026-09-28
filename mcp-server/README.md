# MySpec Local MCP Server

The MySpec MCP server exposes a user's local profile to an existing MCP-capable AI host. The host launches this package as a child process and acts as the MCP client; this repository does not include a separate client application.

The server uses **stdio only**. It reads `~/.myspec/profile.md` on demand and does not write the profile. It provides no authentication, ports, HTTP transport, cloud service, database, telemetry, update check, or network call.

## Requirements

- Python 3.10 or newer.
- Cursor, Claude Desktop, Windsurf, or another MCP host that supports stdio servers.
- A local Markdown profile at `~/.myspec/profile.md` (or a path supplied with `MYSPEC_PROFILE_PATH`).

## Local installation

From this directory, create a virtual environment, activate it, and install the package:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .
```

On macOS/Linux, activate with `source .venv/bin/activate`. The install retrieves the pinned MCP SDK dependency; after installation, server runtime uses local profile I/O and stdio only.

## Host configuration

Use the host's existing MCP server configuration and insert an entry like this, replacing paths with absolute paths on the user's machine:

```json
{
  "mcpServers": {
    "myspec-local": {
      "command": "C:/path/to/MySpec/mcp-server/.venv/Scripts/myspec-mcp-server.exe",
      "args": [],
      "env": {
        "MYSPEC_PROFILE_PATH": "C:/Users/your-name/.myspec/profile.md",
        "MYSPEC_LANG": "en"
      }
    }
  }
}
```

On macOS/Linux, use the executable at `.venv/bin/myspec-mcp-server`. `MYSPEC_PROFILE_PATH` is optional; without it, the server reads `~/.myspec/profile.md`. `MYSPEC_LANG` accepts `en`/`english` or `ar`/`msa`/`ar-MSA`; unsupported values fall back to English.

The host starts and stops the server process. To check package startup manually, run `myspec-mcp-server` from the activated environment; it waits for MCP messages on stdin and stdout. Do not use the command as a regular terminal UI.

## Exposed MCP surface

### Resources

- `myprofile://summary` — concise profile context.
- `myprofile://skills` — skills, learning areas, and skill-related limitations.
- `myprofile://preferences` — communication and output preferences.
- `myprofile://full` — full local profile text.

### Tools

- `get_gap_analysis(project_description)` — returns local skill evidence and explicit technology-term overlap to support host-side gap reasoning. A text match is not a proficiency claim.
- `get_onboarding_plan(topic, minutes=60)` — returns a time-boxed learning agenda informed by the local skill view.

### Prompts

- `onboarding(project_description)` — prepares a project onboarding request with the full local profile context.
- `gap_check(project_description)` — prepares a focused gap analysis with profile evidence and local lexical matches.

The server reads the profile afresh on each call. Missing, unreadable, empty, or malformed files are reported in the resource/tool result; they do not stop the server process.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `MYSPEC_PROFILE_PATH` | `~/.myspec/profile.md` | Override the local profile path. |
| `MYSPEC_LANG` | `en` | Select English or Modern Standard Arabic response labels. |

The profile path is read-only. The local OS process and filesystem permissions are the trust boundary.

## Tests

From this directory, run:

```powershell
python -m unittest discover -s tests -v
```

Tests cover profile parsing and failure cases, resource/tool/prompt registration, environment configuration, and launching the server as a stdio child process.
