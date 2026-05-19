# openaffiliate-wrapper

A tiny MCP server that wraps [openaffiliate.dev](https://openaffiliate.dev) and adds higher-level tools on top of the official registry.

Two tools are exposed:

- **`compare_programs`** — fetches two affiliate programs in parallel and returns a side-by-side comparison table (commission rate, type, cookie window, network, payout terms, restrictions, signup URL).
- **`market_summary`** — pulls every program in a category and returns a small market report: program count, median percentage commission, top three percentage-based programs, top three flat-fee programs, dominant commission type, and a network distribution breakdown.

Built as a learning exercise to understand how the [Model Context Protocol](https://modelcontextprotocol.io) actually works. The official openaffiliate MCP already exposes `search_programs`, `get_program`, and `list_categories` — this wrapper sits in front of those and adds opinionated tools the AI can pick when the user's question matches.

## Why bother?

The wrapper itself is a small thing. The value is what you learn building it:

- How an MCP server declares its tools to an AI client
- Why the tool *description* is the most important field (it's a prompt to the AI)
- How to return structured output the AI can reason over (markdown tables work well)
- How async HTTP calls in parallel speed up tools that touch multiple endpoints
- How to handle messy real-world data — commission rates in this dataset come as strings like `'50%'`, `'15-20%'`, or `'$75 or 20%'`, which need parsing and classifying before any maths is meaningful

## Example output

`market_summary("AI")` returns something like:

> **Programs in this category:** 122
> **Median percentage commission:** 25.0% (across 76 percent-based programs)
> **Dominant commission type:** recurring
>
> **Top 3 by percentage rate**
> - Hostinger — 60% one-time, 30-day cookie, via in-house
> - Leonardo AI — 60% one-time, 30-day cookie, via PartnerStack
> - CustomGPT — 50% recurring, 60-day cookie, via in-house
>
> **Top 3 by flat-fee payout**
> - Expertise AI — $250 one-time, 30-day cookie, via PartnerStack
> - Pilim — $200 one-time, 30-day cookie, via PartnerStack
> - Canva — $36 one-time, 30-day cookie, via Impact

## Quick start

Requires Python 3.10+.

\`\`\`bash
git clone https://github.com/Londonbase/openaffiliate-wrapper.git
cd openaffiliate-wrapper
python3.12 -m venv venv
source venv/bin/activate
pip install "mcp[cli]" httpx
\`\`\`

Then add this to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

\`\`\`json
"openaffiliate-wrapper": {
  "command": "/full/path/to/openaffiliate-wrapper/venv/bin/python",
  "args": ["/full/path/to/openaffiliate-wrapper/server.py"]
}
\`\`\`

Quit and reopen Claude Desktop. Try:

- *"Compare the affiliate programs 'reclaim' and 'motion' using the openaffiliate-wrapper."*
- *"Give me a market summary of the AI category using the openaffiliate-wrapper."*

## What this is not

- Not production code. No tests beyond manual sanity checks. No error retries.
- Not a replacement for the official openaffiliate MCP — it works alongside it.
- Not affiliated with openaffiliate.dev (just a fan of the project).

## Built by

[Zach Measures](https://www.linkedin.com/in/zachmeasures) — first Python project, written with Claude as a teaching companion.