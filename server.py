"""
A tiny MCP server that wraps openaffiliate.dev.

Exposes two tools:
- compare_programs: fetches two affiliate programs and returns a
  side-by-side comparison table.
- market_summary: pulls all programs in a category and returns a
  small market report (program count, median rate, top 3, networks).
"""

import asyncio
import httpx
import re
import sys
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

OPENAFFILIATE_API = "https://openaffiliate.dev/api"

server = Server("openaffiliate-wrapper")


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
        Tool(
            name="market_summary",
            description=(
                "Summarise an entire affiliate-program category from the "
                "openaffiliate registry. Use this whenever the user asks "
                "about the state of a category, market trends, what's "
                "typical, what's standing out, or which networks dominate "
                "a vertical. Returns programme count, median percentage "
                "commission rate, the top three percentage-based programs, "
                "the top three flat-fee programs, the dominant commission "
                "type, and a network distribution breakdown."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": (
                            "The category name to summarise, e.g. 'AI', "
                            "'Productivity', 'Marketing', 'Developer Tools'. "
                            "Case-sensitive — match openaffiliate's category names."
                        ),
                    },
                },
                "required": ["category"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "compare_programs":
        return await do_compare_programs(arguments)
    elif name == "market_summary":
        return await do_market_summary(arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


# ---------------------------------------------------------------
# compare_programs
# ---------------------------------------------------------------
async def do_compare_programs(arguments: dict) -> list[TextContent]:
    slug_a = arguments["slug_a"]
    slug_b = arguments["slug_b"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        a_resp, b_resp = await asyncio.gather(
            client.get(f"{OPENAFFILIATE_API}/programs/{slug_a}"),
            client.get(f"{OPENAFFILIATE_API}/programs/{slug_b}"),
        )

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
| Commission rate | {safe(a, 'commission', 'rate')} | {safe(b, 'commission', 'rate')} |
| Commission type | {safe(a, 'commission', 'type')} | {safe(b, 'commission', 'type')} |
| Cookie window | {a.get('cookieDays', '—')} days | {b.get('cookieDays', '—')} days |
| Network | {a.get('network', '—')} | {b.get('network', '—')} |
| Payout minimum | {safe(a, 'payout', 'minimum')} {safe(a, 'payout', 'currency', default='')} | {safe(b, 'payout', 'minimum')} {safe(b, 'payout', 'currency', default='')} |
| Payout methods | {', '.join(safe(a, 'payout', 'methods', default=[])) or '—'} | {', '.join(safe(b, 'payout', 'methods', default=[])) or '—'} |
| Restrictions | {a.get('restrictions', '—') or '—'} | {b.get('restrictions', '—') or '—'} |
| Signup | {a.get('signupUrl', '—')} | {b.get('signupUrl', '—')} |
""".strip()


# ---------------------------------------------------------------
# Rate parsing
# ---------------------------------------------------------------
def parse_rate(raw):
    """
    Turn a commission rate into a (number, unit) pair, or (None, None)
    if it can't be parsed.

    unit is either 'percent', 'dollar', or 'unknown'.

    Examples:
        '50%'         -> (50.0, 'percent')
        '15-20%'      -> (20.0, 'percent')   # upper bound of a range
        '$75'         -> (75.0, 'dollar')
        '$75 or 20%'  -> (20.0, 'percent')   # prefer percent for hybrids
        30            -> (30.0, 'percent')   # plain numbers assumed percent
        None          -> (None, None)
    """
    if raw is None:
        return (None, None)
    if isinstance(raw, (int, float)):
        return (float(raw), "percent")
    if not isinstance(raw, str):
        return (None, None)

    has_percent = "%" in raw
    has_dollar = "$" in raw

    # If both symbols are present (e.g. '$75 or 20%'), prefer the percent —
    # that's the recurring share, which is usually more interesting.
    if has_percent:
        unit = "percent"
        # Pull only the number adjacent to the % sign
        m = re.findall(r"(\d+(?:\.\d+)?)\s*%", raw)
        if m:
            # For ranges like "15-20%", re.findall gives ["15", "20"];
            # take the upper bound.
            return (float(m[-1]), unit)

    if has_dollar:
        unit = "dollar"
        m = re.findall(r"\$\s*(\d+(?:\.\d+)?)", raw)
        if m:
            return (float(m[-1]), unit)

    # Fallback: find any number, mark unit as unknown
    numbers = re.findall(r"\d+(?:\.\d+)?", raw)
    if numbers:
        return (float(numbers[-1]), "unknown")

    return (None, None)


# ---------------------------------------------------------------
# market_summary
# ---------------------------------------------------------------
async def do_market_summary(arguments: dict) -> list[TextContent]:
    category = arguments["category"]

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{OPENAFFILIATE_API}/programs",
            params={"category": category, "limit": 200},
        )

    if resp.status_code != 200:
        return [TextContent(
            type="text",
            text=f"Could not fetch category '{category}'. Check the category name (try 'AI', 'Productivity', 'Marketing', or 'Developer Tools')."
        )]

    payload = resp.json()
    programs = payload.get("programs") or payload.get("data") or payload
    if not isinstance(programs, list) or len(programs) == 0:
        return [TextContent(
            type="text",
            text=f"No programs found in category '{category}'. The category name is case-sensitive."
        )]

    summary = build_market_summary(category, programs)
    return [TextContent(type="text", text=summary)]


def build_market_summary(category: str, programs: list) -> str:
    """Compute a small market report from a list of program records."""

    # Build two separate lists: percent-based and dollar-based programs.
    percent_programs = []  # list of (rate, program) pairs
    dollar_programs = []

    for p in programs:
        raw = (p.get("commission") or {}).get("rate")
        rate, unit = parse_rate(raw)
        if rate is None:
            continue
        if unit == "percent":
            percent_programs.append((rate, p))
        elif unit == "dollar":
            dollar_programs.append((rate, p))
        # 'unknown' unit programs are skipped from the rankings

    # Median percentage rate.
    percent_rates = [r for r, _ in percent_programs]
    median_rate = None
    if percent_rates:
        sorted_rates = sorted(percent_rates)
        n = len(sorted_rates)
        mid = n // 2
        median_rate = sorted_rates[mid] if n % 2 else (sorted_rates[mid - 1] + sorted_rates[mid]) / 2

    # Top 3 by percent rate.
    percent_programs.sort(key=lambda pair: pair[0], reverse=True)
    top_3_percent = percent_programs[:3]

    # Top 3 by dollar amount.
    dollar_programs.sort(key=lambda pair: pair[0], reverse=True)
    top_3_dollar = dollar_programs[:3]

    # Most common commission type.
    type_counts = {}
    for p in programs:
        t = (p.get("commission") or {}).get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    dominant_type = max(type_counts.items(), key=lambda kv: kv[1])[0] if type_counts else "unknown"

    # Network distribution.
    network_counts = {}
    for p in programs:
        n = p.get("network", "unknown") or "unknown"
        network_counts[n] = network_counts.get(n, 0) + 1
    top_networks = sorted(network_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

    # Format the top-3 lists.
    def fmt_program(rate, p, unit_symbol):
        name = p.get("name") or p.get("slug") or "?"
        commission_type = (p.get("commission") or {}).get("type", "")
        cookie = p.get("cookieDays", "?")
        network = p.get("network") or "?"
        return (
            f"- **{name}** — {rate:g}{unit_symbol} {commission_type}, "
            f"{cookie}-day cookie, via {network}"
        )

    top_percent_lines = "\n".join(
        fmt_program(rate, p, "%") for rate, p in top_3_percent
    ) or "_(no percent-based programs)_"

    top_dollar_lines = "\n".join(
        fmt_program(rate, p, " USD") for rate, p in top_3_dollar
    ) or "_(no flat-fee programs)_"

    network_lines = "\n".join(
        f"- {name}: {count} programs"
        for name, count in top_networks
    ) or "_(no network data)_"

    median_display = f"{median_rate:.1f}%" if median_rate is not None else "could not be computed"

    return f"""## Market summary: {category}

**Programs in this category:** {len(programs)}
**Median percentage commission:** {median_display} (across {len(percent_programs)} percent-based programs)
**Dominant commission type:** {dominant_type}

### Top 3 by percentage rate
{top_percent_lines}

### Top 3 by flat-fee payout
{top_dollar_lines}

### Network distribution (top 5)
{network_lines}
""".strip()


# ---------------------------------------------------------------
# Run the server.
# ---------------------------------------------------------------
async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())