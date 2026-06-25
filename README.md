# Codemagic MCP server

A standalone [MCP](https://modelcontextprotocol.io) server that exposes Codemagic
capabilities as tools for an AI host (Claude Code, Claude Desktop, Cursor,
Antigravity, Windsurf, VS Code, …). It speaks MCP over **stdio**.

## Requirements

- Python ≥ 3.11
- A Codemagic API token

## Install

```bash
git clone https://github.com/Becca-Saka/codemagic-mcp.git
cd codemagic-mcp
```

### Install with uv

```bash
uv sync
```

The server then runs via `uv run --directory <repo> codemagic-mcp` from anywhere,
so the host config never needs to activate the venv.

### Install with pip

```bash
python3 -m venv .venv
.venv/bin/pip install .          # Windows: .venv\Scripts\pip install .
```

This installs the `codemagic-mcp` entry point at `.venv/bin/codemagic-mcp`
(Windows: `.venv\Scripts\codemagic-mcp.exe`), which the host config points at
directly.

## Get your API token

Codemagic → **Account settings** (top-right avatar) → **API token** → **Show** →
**Copy**. Supply it through the `CODEMAGIC_API_TOKEN` env var (below). Until a real
token is set, the tools return `connected: false` with setup instructions.

## Configuration

Every host uses the same server block — only the file location and UI differ.
Replace `/abs/path/to/codemagic-mcp` with the absolute path where you cloned the
repo, and paste your token.

If you installed with **uv**:

```json
{
  "mcpServers": {
    "codemagic": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/to/codemagic-mcp", "codemagic-mcp"],
      "env": { "CODEMAGIC_API_TOKEN": "<your-codemagic-api-token>" }
    }
  }
}
```

If you installed with **pip**, point `command` at the venv binary and drop `args`:

```json
{
  "mcpServers": {
    "codemagic": {
      "command": "/abs/path/to/codemagic-mcp/.venv/bin/codemagic-mcp",
      "env": { "CODEMAGIC_API_TOKEN": "<your-codemagic-api-token>" }
    }
  }
}
```

Pick your host below.

<details>
<summary><b>Claude Code</b></summary>

Easiest is the CLI — with uv:

```bash
claude mcp add codemagic \
  --env CODEMAGIC_API_TOKEN=<your-token> \
  -- uv run --directory /abs/path/to/codemagic-mcp codemagic-mcp
```

Or with pip (point at the venv binary):

```bash
claude mcp add codemagic \
  --env CODEMAGIC_API_TOKEN=<your-token> \
  -- /abs/path/to/codemagic-mcp/.venv/bin/codemagic-mcp
```

Add `-s user` to make it available in every project, or `-s project` to write a
shared `.mcp.json` at the repo root. Or drop the JSON block above into `.mcp.json`
(project) / `~/.claude.json` (user) by hand. Verify with `claude mcp list`.

</details>

<details>
<summary><b>Claude Desktop</b></summary>

**Settings → Developer → Edit Config** opens `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/`,
Windows: `%APPDATA%\Claude\`). Paste the JSON block, save, and **restart** the app.
The tools appear under the 🔌 / tools icon.

</details>

<details>
<summary><b>Cursor</b></summary>

Create `.cursor/mcp.json` in the project (or `~/.cursor/mcp.json` for all
projects) with the JSON block. Then **Settings → MCP** → confirm `codemagic` shows
a green dot. Reload the window if it doesn't.

</details>

<details>
<summary><b>Antigravity</b></summary>

**Settings → MCP Servers → Edit / Add custom server** (or edit
`mcp_config.json` from that pane) and paste the JSON block. Save and reload the
window; the server appears in the MCP panel with its tool list.

</details>

<details>
<summary><b>Windsurf</b></summary>

**Settings → Cascade → MCP Servers → Manage → View raw config**, which opens
`~/.codeium/windsurf/mcp_config.json`. Paste the JSON block, save, and hit
**Refresh**.

</details>

<details>
<summary><b>VS Code (Copilot agent mode)</b></summary>

Add to `.vscode/mcp.json` (workspace) or run **MCP: Add Server** from the command
palette. VS Code nests the block under a top-level `"servers"` key — with uv:

```json
{
  "servers": {
    "codemagic": {
      "command": "uv",
      "args": ["run", "--directory", "/abs/path/to/codemagic-mcp", "codemagic-mcp"],
      "env": { "CODEMAGIC_API_TOKEN": "<your-codemagic-api-token>" }
    }
  }
}
```

Or with pip (point `command` at the venv binary, drop `args`):

```json
{
  "servers": {
    "codemagic": {
      "command": "/abs/path/to/codemagic-mcp/.venv/bin/codemagic-mcp",
      "env": { "CODEMAGIC_API_TOKEN": "<your-codemagic-api-token>" }
    }
  }
}
```

</details>

<details>
<summary><b>Any other MCP host</b></summary>

Point it at the command (uv) `uv run --directory /abs/path/to/codemagic-mcp codemagic-mcp`
or (pip) `/abs/path/to/codemagic-mcp/.venv/bin/codemagic-mcp`, with
`CODEMAGIC_API_TOKEN` in the environment. Transport is stdio.

</details>

## Verify it works

Once configured, ask the host: **"Verify my Codemagic connection."** It should
call `verify_connection` and return your user and teams. If it reports
`connected: false`, the token is missing or wrong.

## Tools

### Account & signing

| Tool | What it does |
| --- | --- |
| `verify_connection` | Verify the Codemagic token (`GET /user`) and list the teams it can access. |
| `get_team_signing` | List a team's uploaded code-signing identities (certs, profiles, keystores). |
| `get_team_integrations` | List a team's configured integrations and tester groups. |

### Applications

| Tool | What it does |
| --- | --- |
| `list_applications` | List the Codemagic apps the token can access. |
| `get_application` | Get one app's full config: workflows, scripts, build settings, signing, publishing. |
| `add_application` | Add a new application to Codemagic from a git repository. |
| `delete_application` | Permanently delete an application from Codemagic. |

### Environment variables

| Tool | What it does |
| --- | --- |
| `list_variable_groups` | List variable groups (and their variable keys) for an app or team. |
| `create_variable_group` | Create an environment variable group on an app or a team. |
| `update_variable_group` | Rename a group or change which apps may read it (advanced security). |
| `delete_variable_group` | Delete a variable group and all the variables in it. |
| `add_environment_variables` | Add environment variables to an existing variable group. |
| `update_environment_variable` | Update a single variable's value, name, or secure flag. |
| `delete_environment_variable` | Delete a single environment variable from a group. |

### Builds

| Tool | What it does |
| --- | --- |
| `list_team_builds` | List recent builds for a Codemagic team. |
| `get_build_info` | Get a build's status, app/repo, commit, timing, and per-step status. |
| `get_build_step_logs` | Fetch raw log text for a build's steps. |
| `start_build` | Trigger a new build. **Starts a real build and consumes build minutes.** |
| `cancel_build` | Cancel a running Codemagic build. |
| `diagnose_build_failure` | Required first step for any failed-build question — returns the diagnosis playbook. |

### codemagic.yaml authoring

| Tool | What it does |
| --- | --- |
| `create_codemagic_yaml` | Required first step before writing any codemagic.yaml — returns the authoring playbook. |
| `migrate_ui_to_yaml` | Required first step before migrating a Workflow Editor app to codemagic.yaml. |
| `codemagic_yaml_reference` | Get detailed reference notes for one part of a codemagic.yaml. |
| `validate_codemagic_yaml` | Validate a codemagic.yaml against the official Codemagic JSON schema. |

## Security

Treat your API token like a password. Prefer per-user config files outside version
control over committing it. The repo's `.gitignore` excludes `.env` and `.mcp.json`
to help avoid leaking it.
