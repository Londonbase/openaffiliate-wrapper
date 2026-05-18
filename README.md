# openaffiliate-wrapper

A tiny MCP server that wraps [openaffiliate.dev](https://openaffiliate.dev) and adds one extra tool:

- **`compare_programs`** — fetches two affiliate programs in parallel and returns a side-by-side comparison table (commission rate, type, cookie window, network, payout terms, restrictions, signup URL).

Built as a learning exercise to understand how the [Model Context Protocol](https://modelcontextprotocol.io) actually works. The official openaffiliate MCP already exposes `search_programs`, `get_program`, and `list_categories` — this wrapper sits in front of those and adds a higher-level tool the AI can pick when the user asks to compare two specific programs.

## Why bother?

The wrapper itself is a small thing. The value is in what you learn building it:

- How an MCP server declares its tools to an AI client
- Why the tool *description* is the most important field (it's a prompt to the AI)
- How to return structured output the AI can reason over (markdown tables work well)
- How async HTTP calls in parallel speed up a tool that touches multiple endpoints

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

Quit and reopen Claude Desktop. Ask: *"Compare the affiliate programs 'reclaim' and 'motion' using the openaffiliate-wrapper."*

## What this is not

- Not production code. No tests beyond a manual sanity check. No error retries.
- Not a replacement for the official openaffiliate MCP — it works alongside it.
- Not affiliated with openaffiliate.dev (just a fan of the project).

## Built by

[Zach Measures](https://www.linkedin.com/in/zachmeasures
) — first Python project, written with Claude as a teaching companion.