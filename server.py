"""
A tiny MCP server that wraps openaffiliate.dev.

Exposes one extra tool — compare_programs — which fetches two
affiliate programs from openaffiliate's API and returns a clean
side-by-side comparison table.

The AI then writes the human-readable summary on top of that table.
"""

import asyncio
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# The base URL for openaffiliate's public API.
OPENAFFILIATE_API = "https://openaffiliate.dev/api"

# Create the server. The name is what the AI sees when it lists
# available tool sources.
server = Server("openaffiliate-wrapper")


# ---------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------
# The @server.list_tools decorator registers a function that tells
# the AI "here are the tools I offer". The description field is the
# most important thing here — the AI reads it to decide whether to
# use your tool.
# ---------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="compare_programs",
            description=(
                "Compare two affiliate programs from the openaffiliate "
                "registry side by side. Use this whenever the user asks "
                "to compare, contrast, or choose between two specific "
                "affiliate programs by name or slug. Returns commission "
                "rate, cookie window, network, payout terms, and "
                "restrictions for each program in a structured table."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug_a": {
                        "type": "string",
                        "description": "First program slug, e.g. 'reclaim' or 'notion'",
                    },
                    "slug_b": {
                        "type": "string",
                        "description": "Second program slug, e.g. 'motion' or 'gamma'",
                    },
                },
                "required": ["slug_a", "slug_b"],
            },
        ),
    ]


# ---------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------
# When the AI decides to call compare_programs, this function runs.
# It fetches both programs in parallel, then formats a markdown
# table for the AI to read.
# ---------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name != "compare_programs":
        raise ValueError(f"Unknown tool: {name}")

    slug_a = arguments["slug_a"]
    slug_b = arguments["slug_b"]

    # Fetch both programs in parallel — twice as fast as sequential.
    async with httpx.AsyncClient(timeout=10.0) as client:
        a_resp, b_resp = await asyncio.gather(
            client.get(f"{OPENAFFILIATE_API}/programs/{slug_a}"),
            client.get(f"{OPENAFFILIATE_API}/programs/{slug_b}"),
        )

    # Handle the case where one of the slugs wasn't found.
    if a_resp.status_code != 200:
        return [TextContent(type="text", text=f"Could not find program '{slug_a}'. Check the spelling of the slug.")]
    if b_resp.status_code != 200:
        return [TextContent(type="text", text=f"Could not find program '{slug_b}'. Check the spelling of the slug.")]

    a = a_resp.json()
    b = b_resp.json()

    table = build_comparison(a, b)
    return [TextContent(type="text", text=table)]


def build_comparison(a: dict, b: dict) -> str:
    """Format two program records as a markdown comparison table."""

    def safe(d: dict, *keys, default="—"):
        """Walk a nested dict safely. Returns default if any key is missing."""
        for k in keys:
            if not isinstance(d, dict):
                return default
            d = d.get(k)
            if d is None:
                return default
        return d

    return f"""
| Field | {a.get('name', a.get('slug', 'A'))} | {b.get('name', b.get('slug', 'B'))} |
|---|---|---|
| Commission rate | {safe(a, 'commission', 'rate')}% | {safe(b, 'commission', 'rate')}% |
| Commission type | {safe(a, 'commission', 'type')} | {safe(b, 'commission', 'type')} |
| Cookie window | {a.get('cookieDays', '—')} days | {b.get('cookieDays', '—')} days |
| Network | {a.get('network', '—')} | {b.get('network', '—')} |
| Payout minimum | {safe(a, 'payout', 'minimum')} {safe(a, 'payout', 'currency', default='')} | {safe(b, 'payout', 'minimum')} {safe(b, 'payout', 'currency', default='')} |
| Payout methods | {', '.join(safe(a, 'payout', 'methods', default=[])) or '—'} | {', '.join(safe(b, 'payout', 'methods', default=[])) or '—'} |
| Restrictions | {a.get('restrictions', '—') or '—'} | {b.get('restrictions', '—') or '—'} |
| Signup | {a.get('signupUrl', '—')} | {b.get('signupUrl', '—')} |
""".strip()


# ---------------------------------------------------------------
# Run the server. This is what makes it talk to Claude Desktop
# over stdin/stdout (the "stdio" transport).
# ---------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())