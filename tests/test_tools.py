import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module")
def server_module(monkeypatch_module=None):
    import os

    os.environ.setdefault("STE_DATA_DIR", str(REPO_ROOT / "data"))
    from ste_mcp import server

    return server


@pytest.mark.anyio
async def test_list_tools_exposes_four_tools(server_module):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    async with client_session(server_module.mcp._mcp_server) as client:
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert names == {"check_word", "check_text", "lookup_technical_term", "dictionary_info"}


@pytest.mark.anyio
async def test_check_word_via_client(server_module):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    async with client_session(server_module.mcp._mcp_server) as client:
        result = await client.call_tool("check_word", {"word": "abaft"})
        payload = result.structuredContent
        assert payload["status"] == "non_ste"
        assert payload["senses"][0]["alternative"]["word"] == "AFT OF"


@pytest.mark.anyio
async def test_check_text_via_client(server_module):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    async with client_session(server_module.mcp._mcp_server) as client:
        result = await client.call_tool(
            "check_text", {"text": "Please utilize the abaft compartment."}
        )
        payload = result.structuredContent
        assert payload["summary"]["non_ste"] >= 1
        # "utilize" is itself a dictionary entry in this snapshot (non-STE), so
        # it is classified as non_ste rather than unknown (see test_matcher.py).
        assert any(e["word"] == "utilize" for e in payload["non_ste"])
        assert any(e["word"] == "Please" for e in payload["unknown"])


@pytest.mark.anyio
async def test_lookup_technical_term_via_client(server_module):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    async with client_session(server_module.mcp._mcp_server) as client:
        found = await client.call_tool("lookup_technical_term", {"term": "2D"})
        assert found.structuredContent["found"] is True

        missing = await client.call_tool("lookup_technical_term", {"term": "not-a-real-term-xyz"})
        assert missing.structuredContent["found"] is False


@pytest.mark.anyio
async def test_dictionary_info_via_client(server_module):
    from mcp.shared.memory import create_connected_server_and_client_session as client_session

    async with client_session(server_module.mcp._mcp_server) as client:
        result = await client.call_tool("dictionary_info", {})
        payload = result.structuredContent
        assert payload["source"] == "ste.valaratomics.com"
        assert payload["terms_total"] > 0
