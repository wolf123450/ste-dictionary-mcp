# STE Dictionary MCP Server

An MCP server that checks text against ASD-STE100 Simple Technical English
(STE): which words are approved, which aren't, and what STE word replaces
each violation. Works entirely offline from a static dictionary snapshot in
`data/` — no network access at runtime. See
`docs/superpowers/specs/2026-08-21-ste-mcp-design.md` for the full design.

## Setup

```bash
pip install -r requirements.txt
python scripts/download_nltk_data.py
pytest
```

The `check_structure` tool needs two small NLTK data packages (the
`punkt_tab` sentence/word tokenizer and the `averaged_perceptron_tagger_eng`
POS tagger -- classic statistical models, not deep learning). Running
`python scripts/download_nltk_data.py` once after installing dependencies
downloads them and trims out the non-English tokenizer languages NLTK's
downloader pulls by default, keeping the on-disk footprint to a few MB
instead of ~58MB. It's safe to re-run. If you skip this step, `check_structure`
raises a `RuntimeError` telling you to run it.

The server reads its dictionary snapshot from the `STE_DATA_DIR` environment
variable, defaulting to `./data` (relative to the working directory the
server is launched from). The snapshot in `data/` is committed to this repo,
so no separate download step is needed.

## Running standalone

```bash
python -m ste_mcp.server
```

Speaks MCP over stdio.

## Installing into Claude Code

Register the server with the Claude Code CLI. Use an absolute path to your
Python interpreter if `python` on your `PATH` doesn't have the `mcp` package
installed.

**Local scope** (available only when Claude Code is run from this repo):

```bash
cd /absolute/path/to/ste-dictionary-mcp
claude mcp add --transport stdio --env STE_DATA_DIR=/absolute/path/to/ste-dictionary-mcp/data ste-dictionary -- python -m ste_mcp.server
```

**User scope** (available from any directory). Because user-scope servers
don't run with this repo as their working directory, wrap the launch in a
small script that `cd`s into the repo first, e.g. `~/.claude/ste-launcher.sh`:

```bash
#!/bin/sh
cd /absolute/path/to/ste-dictionary-mcp
exec python -m ste_mcp.server
```

Then register it:

```bash
chmod +x ~/.claude/ste-launcher.sh
claude mcp add --transport stdio --scope user --env STE_DATA_DIR=/absolute/path/to/ste-dictionary-mcp/data ste-dictionary -- ~/.claude/ste-launcher.sh
```

Verify with `claude mcp list`, or `/mcp` inside a session.

## Claude Desktop configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ste-dictionary": {
      "command": "python",
      "args": ["-m", "ste_mcp.server"],
      "cwd": "/absolute/path/to/ste-dictionary-mcp",
      "env": {
        "STE_DATA_DIR": "/absolute/path/to/ste-dictionary-mcp/data"
      }
    }
  }
}
```

## Tools

| Tool | Purpose |
|---|---|
| `check_word(word)` | Is this word/phrase STE, and what replaces it? |
| `check_text(text, include_unknown=True)` | Scan a document for non-STE, ambiguous, unknown, and technical words with positions. |
| `check_structure(text)` | Scan a document for structural STE violations: overlong sentences, passive voice, non-imperative mood, noun clusters of 4+, overlong paragraphs, gerund-as-noun. |
| `lookup_technical_term(term)` | Look up an approved technical term or abbreviation. |
| `dictionary_info()` | Dictionary source, freshness, and coverage stats. |

`check_word`/`check_text` are word-list-based, not a grammar checker: they
check vocabulary, not sentence structure. `check_structure` adds lightweight
structural checks (via a small statistical POS tagger, not a full grammar
engine) for the ASD-STE100 rules a word list can't catch -- see its
docstring in `ste_mcp/structure.py` for the exact rules and their heuristic
limitations. It is diagnostic only (no rewrite suggestions); the agent using
these tools is responsible for rewriting.

Some words have both an STE-approved sense and a non-STE sense (e.g. "long"
as a plain adjective is STE, but "as long as"/"no longer" is not). For those,
`check_word` returns `status: "ambiguous"` (instead of `"non_ste"`) along
with a `note` telling the caller to verify which sense applies in context,
and `check_text` reports them in a separate `ambiguous` bucket/summary count
rather than `non_ste`. `status: "non_ste"` is reserved for words where every
matched sense is non-STE.
