---
name: kiro-cli
description: "Delegate tasks to kiro-cli as a subagent — Claude models with 57 tools and MCP servers."
version: 1.0.0
author: stabgan
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Coding-Agent, Claude, Kiro, Subagent, MCP, Local, Automation]
    related_skills: [claude-code, hermes-agent, codex]
---

# kiro-cli — Hermes Subagent Orchestration Guide

Delegate tasks to [kiro-cli](https://kiro.dev) as a subagent from Hermes. kiro-cli provides Claude models (Opus 4.6, Sonnet 4.6, Haiku 4.5 + DeepSeek, MiniMax, GLM, Qwen) with 57 built-in tools and 5 active MCP servers — all running locally.

## Prerequisites

- **Binary:** `~/.local/bin/kiro-cli` (installed via Kiro IDE or standalone)
- **Auth:** `kiro-cli login` (IAM Identity Center)
- **Verify:** `kiro-cli --version` (requires v2.x+)
- **Models:** `kiro-cli chat --list-models` to see available models

## Two Orchestration Modes

### Mode 1: Print Mode (`--no-interactive`) — Non-Interactive (PREFERRED)

Runs a one-shot task, returns the result, and exits. No PTY needed.

```
terminal(command="echo 'Your task here' | kiro-cli chat --no-interactive --model claude-opus-4.6 --trust-all-tools --wrap never", workdir="/path/to/project", timeout=180)
```

**When to use:**
- One-shot coding tasks (fix a bug, add a feature, refactor)
- Research tasks (search docs, read papers, web search)
- File operations (read, write, analyze)
- Any task where you don't need multi-turn conversation

**Key flags:**
- `--no-interactive` — Essential. Prevents waiting for stdin after first message.
- `--trust-all-tools` — Auto-approves all tool use (no blocking prompts).
- `--wrap never` — Raw output without terminal width wrapping.
- `--model <model>` — Choose the model (default: auto).

### Mode 2: Interactive via tmux — Multi-Turn Sessions

For complex multi-step work requiring follow-up prompts.

```
# Start tmux session
terminal(command="tmux new-session -d -s kiro-work -x 140 -y 40")

# Launch kiro-cli
terminal(command="tmux send-keys -t kiro-work 'cd /path/to/project && kiro-cli chat --model claude-opus-4.6 --trust-all-tools' Enter")

# Wait for startup, send task
terminal(command="sleep 3 && tmux send-keys -t kiro-work 'Refactor the auth module' Enter")

# Monitor progress
terminal(command="sleep 20 && tmux capture-pane -t kiro-work -p -S -50")

# Send follow-up
terminal(command="tmux send-keys -t kiro-work 'Now add tests' Enter")

# Exit
terminal(command="tmux send-keys -t kiro-work '/quit' Enter")
```

## Available Models

| Model | Context | Speed | Best For |
|-------|---------|-------|----------|
| `claude-opus-4.6` | 1M tokens | Slow | Complex reasoning, architecture, planning |
| `claude-sonnet-4.6` | 1M tokens | Medium | Balanced coding, general tasks |
| `claude-haiku-4.5` | 200K | Fast | Quick questions, simple edits |
| `deepseek-3.2` | 164K | Fast | Code generation (cheap) |
| `qwen3-coder-next` | 256K | Fast | Code-focused tasks (cheapest) |

## Built-in Tools (57 total)

kiro-cli has these tools available during inference:

### File System
- `fs_read` — Read files
- `fs_write` — Write/create files
- `glob` — File pattern matching
- `grep` — Text search

### Execution
- `execute_bash` — Run shell commands
- `code` — Code execution

### Web & Research
- `web_search` — Web search
- `web_fetch` — Fetch URL content
- `tavily_search`, `tavily_crawl`, `tavily_extract`, `tavily_map`, `tavily_research`

### Browser (Playwright MCP)
- `browser_navigate`, `browser_click`, `browser_snapshot`, `browser_type`
- `browser_evaluate`, `browser_take_screenshot`, `browser_fill_form`
- Full browser automation (25 tools total)

### Academic (arxiv MCP)
- `search_papers`, `download_paper`, `read_paper`, `get_abstract`
- `semantic_search`, `citation_graph`, `watch_topic`, `check_alerts`

### Documentation (Context7 MCP)
- `resolvelibraryid` — Find library documentation
- `querydocs` — Query library docs with code examples

### Reasoning (steelmind MCP)
- `think` — Structured reasoning step
- `verify` — Critical self-assessment

### Agent
- `use_subagent` — Delegate to kiro-cli's own subagents
- `session` — Session management
- `knowledge` — Knowledge base
- `todo_list` — Task tracking

## Task Delegation Patterns

### Pattern 1: Research & Report

```
terminal(command="echo 'Research the latest best practices for Python async error handling. Search the web, read relevant documentation, and provide a summary with code examples.' | kiro-cli chat --no-interactive --model claude-opus-4.6 --trust-all-tools --wrap never", timeout=120)
```

### Pattern 2: Code Generation

```
terminal(command="echo 'Read all files in src/api/ and create a comprehensive test suite in tests/test_api.py using pytest. Cover all endpoints with happy path and error cases.' | kiro-cli chat --no-interactive --model claude-sonnet-4.6 --trust-all-tools --wrap never", workdir="/path/to/project", timeout=180)
```

### Pattern 3: Bug Investigation

```
terminal(command="echo 'The tests in tests/test_auth.py are failing with a 401 error. Read the test file, the auth module, and any related config. Diagnose the root cause and fix it.' | kiro-cli chat --no-interactive --model claude-opus-4.6 --trust-all-tools --wrap never", workdir="/path/to/project", timeout=180)
```

### Pattern 4: Documentation Lookup

```
terminal(command="echo 'Use the querydocs tool to look up how to implement WebSocket connections in FastAPI. Include code examples.' | kiro-cli chat --no-interactive --model claude-haiku-4.5 --trust-all-tools --wrap never", timeout=60)
```

### Pattern 5: Web Research

```
terminal(command="echo 'Search the web for the latest release notes of React 19. Summarize the key changes and breaking changes.' | kiro-cli chat --no-interactive --model claude-haiku-4.5 --trust-all-tools --wrap never", timeout=60)
```

### Pattern 6: Multi-File Refactoring

```
terminal(command="echo 'Refactor all database queries in src/db/ to use async/await with SQLAlchemy 2.0 syntax. Update imports, session handling, and ensure all tests still pass.' | kiro-cli chat --no-interactive --model claude-opus-4.6 --trust-all-tools --wrap never", workdir="/path/to/project", timeout=300)
```

### Pattern 7: Paper Research

```
terminal(command="echo 'Search arxiv for recent papers on \"retrieval augmented generation\" from 2024-2025. Download the top 3 most relevant papers and summarize their key contributions and methods.' | kiro-cli chat --no-interactive --model claude-sonnet-4.6 --trust-all-tools --wrap never", timeout=180)
```

### Pattern 8: Browser Automation

```
terminal(command="echo 'Navigate to https://example.com/dashboard, take a screenshot, and describe what you see on the page.' | kiro-cli chat --no-interactive --model claude-sonnet-4.6 --trust-all-tools --wrap never", timeout=60)
```

## Parallel Execution

Run multiple kiro-cli tasks simultaneously:

```
# Task 1: Backend
terminal(command="echo 'Fix the auth bug' | kiro-cli chat --no-interactive --model claude-sonnet-4.6 --trust-all-tools --wrap never > /tmp/task1.txt 2>&1 &")

# Task 2: Frontend
terminal(command="echo 'Update the login form UI' | kiro-cli chat --no-interactive --model claude-sonnet-4.6 --trust-all-tools --wrap never > /tmp/task2.txt 2>&1 &")

# Task 3: Tests
terminal(command="echo 'Write integration tests' | kiro-cli chat --no-interactive --model claude-haiku-4.5 --trust-all-tools --wrap never > /tmp/task3.txt 2>&1 &")

# Wait and collect results
terminal(command="wait && cat /tmp/task1.txt /tmp/task2.txt /tmp/task3.txt")
```

## Using Specific Agents

kiro-cli supports named agents with custom system prompts and MCP configs:

```
# List available agents
terminal(command="kiro-cli agent list")

# Use a specific agent
terminal(command="echo 'Your task' | kiro-cli chat --no-interactive --agent 'AWS Expert' --model claude-opus-4.6 --trust-all-tools --wrap never", timeout=120)
```

## Session Management

```
# List past sessions
terminal(command="kiro-cli chat --list-sessions")

# Resume a session (interactive only)
terminal(command="kiro-cli chat --resume")

# Resume specific session
terminal(command="kiro-cli chat --resume-id <SESSION_ID>")
```

## MCP Server Management

kiro-cli manages its own MCP servers. View and configure them:

```
# List configured servers
terminal(command="kiro-cli mcp list")

# Check server status
terminal(command="kiro-cli mcp status --name Context7")

# Add a new server
terminal(command="kiro-cli mcp add --name my-server --command npx --args '-y,@my/mcp-server@latest'")

# Remove a server
terminal(command="kiro-cli mcp remove --name my-server")
```

### Currently Active MCP Servers
- **Context7** — Library documentation lookup (npx)
- **arxiv** — Academic paper search/download (uvx)
- **playwright** — Browser automation (npx)
- **steelmind** — Structured reasoning (npx)
- **tavily-remote** — Web search, extract, crawl (npx)

## Output Cleaning

kiro-cli output includes metadata (spinners, timing, tool execution logs). When parsing output programmatically, strip:
- Lines starting with `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏` (spinners)
- Lines starting with `▸ Time:` (timing)
- Lines containing "All tools are now trusted" (startup noise)
- Lines starting with `> ` (output prefix — strip the prefix, keep content)
- Lines matching `[N.N]` (timing markers)

## Integration with Hermes

### As LLM Backbone (via kiro-openai-wrapper)

kiro-cli serves as Hermes Agent's LLM backbone through an OpenAI-compatible wrapper:

```
# Start wrapper (Terminal 1)
python ~/Development/hermes/kiro-openai-wrapper/main.py

# Hermes uses it automatically via config:
# provider: custom
# api_base: http://localhost:8000/v1
# model: claude-opus-4.6
```

### As Subagent (via terminal tool)

Hermes delegates specific tasks to kiro-cli for its superior tool access:

```
# From within Hermes, delegate a research task
terminal(command="echo 'Search for Python async patterns' | ~/.local/bin/kiro-cli chat --no-interactive --model claude-haiku-4.5 --trust-all-tools --wrap never", timeout=60)
```

### When to Use kiro-cli vs Hermes Tools

| Task | Use kiro-cli | Use Hermes tools |
|------|-------------|-----------------|
| Web search/research | ✅ (tavily, web_search) | ❌ |
| Browser automation | ✅ (playwright) | ❌ |
| Academic papers | ✅ (arxiv) | ❌ |
| Library docs | ✅ (Context7) | ❌ |
| File read/write | Either | ✅ (native, faster) |
| Shell commands | Either | ✅ (native, faster) |
| Memory/skills | ❌ | ✅ (persistent) |
| Multi-turn planning | ❌ | ✅ (goals, todo) |

**Rule of thumb:** Use kiro-cli for tasks requiring MCP tools (web, browser, papers, docs). Use Hermes native tools for file operations and persistent state.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "command not found" | Check `~/.local/bin/kiro-cli` exists and is in PATH |
| Auth expired | Run `kiro-cli login` |
| MCP server failed | `kiro-cli mcp status --name <server>` |
| Timeout | Increase timeout or use a faster model (haiku) |
| Empty output | kiro-cli may have only produced metadata — check raw output |
| Model not available | `kiro-cli chat --list-models` to see current options |
