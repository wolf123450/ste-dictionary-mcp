# STE Dictionary MCP Server

An MCP server that checks text against ASD-STE100 Simple Technical English
(STE): which words are approved, which aren't, and what STE word replaces
each violation. Works entirely offline from a static dictionary snapshot in
`data/` — no network access at runtime. See
`docs/superpowers/specs/2026-08-21-ste-mcp-design.md` for the full design.

## Setup

```bash
pip install -r requirements.txt
pytest
```

The server reads its dictionary snapshot from the `STE_DATA_DIR` environment
variable, defaulting to `./data` (relative to the working directory the
server is launched from). To refresh the snapshot, re-run
`download_ste_dictionary.py` and restart the server.

## Running standalone

```bash
python -m ste_mcp.server
```

Speaks MCP over stdio.

## Claude Desktop / Claude Code configuration

Add to your MCP client's config (e.g. `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "ste-dictionary": {
      "command": "python",
      "args": ["-m", "ste_mcp.server"],
      "cwd": "/absolute/path/to/STE-dictonary-MCP",
      "env": {
        "STE_DATA_DIR": "/absolute/path/to/STE-dictonary-MCP/data"
      }
    }
  }
}
```

## Tools

| Tool | Purpose |
|---|---|
| `check_word(word)` | Is this word/phrase STE, and what replaces it? |
| `check_text(text, include_unknown=True)` | Scan a document for non-STE, unknown, and technical words with positions. |
| `lookup_technical_term(term)` | Look up an approved technical term or abbreviation. |
| `dictionary_info()` | Dictionary source, freshness, and coverage stats. |

The check is word-list-based, not a grammar checker: it does not enforce
sentence-structure rules (one idea per sentence, active voice, imperative
mood). The agent using these tools is responsible for rewriting and for
structural STE compliance.
