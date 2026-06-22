# Codemagic MCP server

A standalone MCP server exposing Codemagic capabilities as tools for an IDE host
model (Claude Code, Cursor, …). See [doc/IMPLEMENTATION_PLAN.md](doc/IMPLEMENTATION_PLAN.md).

## Tools

- `verify_connection` — checks the token via `GET /api/v3/user`, returns the user and teams.
- `list_team_builds` — recent builds for a team (auto-resolves when you have one team).

## Authentication

The Codemagic API token is supplied via the `CODEMAGIC_API_TOKEN` env var in your
MCP config (the standard pattern, e.g. LangSmith). Until a real token is set, the
tools return `connected: false` with setup instructions.

### Get your API token

Codemagic → **Account settings** (top-right avatar) → **API token** → **Show** → **Copy**.

## IDE config (Claude Code / Cursor)

Same block for either IDE (Claude Code: `.mcp.json`; Cursor: `.cursor/mcp.json`).
Replace the placeholder with your token, then reload the IDE:

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
