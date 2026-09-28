# Phase 8: Local-First MySpec MCP Server

## Objective

Phase 8 implements MySpec's Tier 1 integration as an open-source, local-only Model Context Protocol server. A user's existing AI host (such as Cursor, Claude Desktop, or Windsurf) launches the server as a child process over stdio and remains the MCP client. The server reads the user's profile from `~/.myspec/profile.md` and supplies profile context and planning operations without transmitting user data off-device.

## Architecture

- **Host-owned process lifecycle:** The MCP host starts and stops the server as a local child process. JSON-RPC messages use stdin/stdout through MCP stdio transport; stdout is reserved for protocol traffic and diagnostics go to stderr.
- **Local profile source:** Read `~/.myspec/profile.md` by default. `MYSPEC_PROFILE_PATH` optionally overrides the path; `MYSPEC_LANG` selects English or Arabic MSA response labels and defaults to English.
- **Read-only profile access:** Read the profile on each request so host sessions can see local edits. Resources and tools never write or mutate the profile.
- **Graceful input handling:** Missing, unreadable, empty, and malformed profiles produce clear status context rather than process crashes. Markdown remains readable source text; JSON profile content is parsed and validated as an object before structured extraction.
- **MCP resources:** `myprofile://summary`, `myprofile://skills`, `myprofile://preferences`, and `myprofile://full` expose focused profile context.
- **MCP tools:** `get_gap_analysis(project_description)` returns local profile evidence and project terms for host-assisted gap analysis. `get_onboarding_plan(topic, minutes=60)` returns a time-boxed learning outline informed by available profile data.
- **MCP prompts:** `onboarding(project_description)` and `gap_check(project_description)` package project context, profile state, and instructions for the host model.
- **Trust boundary:** The local operating system's process and filesystem permissions control access. Tier 1 includes no authentication, OAuth, tokens, API keys, ports, remote transport, cloud services, database, telemetry, tracking, update checks, or network calls.

## Expected Folder and File Structure

```text
mcp-server/
├── pyproject.toml
├── README.md
├── .gitignore
├── src/
│   └── myspec_mcp_server/
│       ├── __init__.py
│       ├── __main__.py
│       ├── profile.py
│       └── server.py
└── tests/
    ├── test_profile.py
    └── test_server.py
```

## Implementation Workflow

1. **Create the Python package:** Define a lightweight installable package and pin the supported MCP SDK release line. Provide a module entry point suitable for host child-process configuration.
2. **Resolve local configuration:** Select the default profile path and apply `MYSPEC_PROFILE_PATH` and `MYSPEC_LANG` overrides.
3. **Load and classify profile content:** Read the profile on demand, distinguish Markdown and JSON content, extract focused views, and return useful missing/malformed status messages.
4. **Register resources:** Expose summary, skills, preferences, and full-profile views under the specified stable URIs.
5. **Register tools:** Implement evidence-oriented project gap analysis and a duration-aware pre-flight learning plan. Keep heuristic term matching explicit about its limits so lexical overlap is not presented as proven proficiency.
6. **Register prompts:** Provide onboarding and gap-check prompt templates that inject the local profile context into the host's LLM workflow.
7. **Serve via stdio:** Start only the stdio transport from the package entry point; emit no protocol-corrupting stdout logs.
8. **Document host configuration:** Explain local installation and provide a host configuration example using the installed server executable and environment overrides. Hosts use their own MCP support; MySpec ships no client.
9. **Validate locally:** Add unit and MCP-surface tests for profile parsing, missing/malformed files, resources, tools, prompts, default configuration, and transport behavior.

## Requirements and Constraints

- The server is a local stdio child process and supports existing MCP hosts as clients.
- The default profile is `~/.myspec/profile.md`, with optional `MYSPEC_PROFILE_PATH` and `MYSPEC_LANG` environment overrides.
- The server exposes exactly the four specified resources, two tools, and two prompts.
- Profile reads are local, request-scoped, and read-only; missing or malformed data must not crash the server.
- Tool output distinguishes observed profile text from heuristic matches and inferred analysis.
- Server output on stdout is MCP protocol only; operational diagnostics use stderr.
- Local OS permissions are the trust boundary. The process does not add authentication or remote access.
- Runtime behavior contains no network requests, listeners, ports, cloud dependencies, databases, telemetry, tracking, or update checks.
- The Tier 2 remote/cloud design remains out of scope.

## Validation Criteria

1. A host can launch the server as a child process and discover the required resources, tools, and prompts over stdio.
2. Each resource URI returns its intended view of the local profile, using the configured language labels where supported.
3. Both tools validate arguments, return useful results for valid inputs, and handle absent profile data without crashing.
4. Both prompt templates include the relevant project description and current local profile context.
5. Missing, empty, malformed JSON, unreadable, and valid Markdown/JSON profile cases are covered by tests.
6. Tests verify the default path, both environment overrides, tool defaults, and the complete MCP surface.
7. Source inspection confirms the server starts only stdio transport, makes no network calls, and never writes profile data.
8. Installation and host configuration steps work locally without a separate MySpec MCP client.

## Scope Boundary

Phase 8 implements only the local Tier 1 MCP server and its local setup, tests, and documentation. The MCP host owns client behavior and process lifecycle. Remote HTTP transports, ports, authentication, cloud services, databases, profile synchronization, and other Tier 2 architecture are excluded.
