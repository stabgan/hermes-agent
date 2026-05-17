# kiro-cli Complete Reference

**Version:** 2.2.2  
**Binary:** `~/.local/bin/kiro-cli`  
**Auth:** IAM Identity Center (AWS)

---

## Table of Contents
1. [Global Options](#global-options)
2. [Commands Reference](#commands-reference)
3. [Chat Command (Primary Interface)](#chat-command)
4. [MCP (Model Context Protocol)](#mcp)
5. [Agent Management](#agent-management)
6. [Available Models](#available-models)
7. [Available Tools (Built-in)](#available-tools)
8. [Settings](#settings)
9. [MCP vs Hermes: Which Harness?](#mcp-harness-recommendation)

---

## Global Options

| Flag | Description |
|------|-------------|
| `-v, --verbose...` | Increase logging verbosity (stackable) |
| `--help-all` | Print help for ALL subcommands |
| `--agent <AGENT>` | Launch chat with specified agent |
| `--tui` | Launch chat in TUI mode |
| `--classic` | Launch chat in classic (legacy) UI mode |
| `-h, --help` | Print help |
| `-V, --version` | Print version |

---

## Commands Reference

| Command | Description |
|---------|-------------|
| `chat` | AI assistant in your terminal (main interface) |
| `mcp` | Model Context Protocol server management |
| `agent` | Manage AI agents (create, list, edit, validate) |
| `acp` | Agent Client Protocol (ACP) agent |
| `translate` | Natural Language to Shell translation |
| `inline` | Inline shell completions |
| `settings` | Customize appearance & behavior |
| `doctor` | Fix and diagnose common issues |
| `login` | Login |
| `logout` | Logout |
| `whoami` | Print current user details |
| `profile` | Show IDC user profile |
| `user` | Manage your account |
| `setup` | Setup CLI components |
| `update` | Update the Kiro application |
| `diagnostic` | Run diagnostic tests |
| `init` | Generate shell dotfiles (bash/zsh/fish/nu) |
| `theme` | Get or set theme |
| `issue` | Create a new GitHub issue |
| `launch` | Launch the desktop app |
| `quit` | Quit the desktop app |
| `restart` | Restart the desktop app |
| `integrations` | Manage system integrations |
| `dashboard` | Open the dashboard |
| `debug` | Debug the app |

---

## Chat Command

**The primary interface for LLM interaction.**

```bash
kiro-cli chat [OPTIONS] [INPUT]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `[INPUT]` | The first question to ask (optional) |

### Options

| Flag | Description |
|------|-------------|
| `-r, --resume` | Resume most recent conversation from this directory |
| `--resume-id <SESSION_ID>` | Resume a specific conversation by session ID |
| `--resume-picker` | Interactively select a conversation to resume |
| `--agent <AGENT>` | Context profile to use |
| `--model <MODEL>` | Model to use |
| `-a, --trust-all-tools` | Allow model to use any tool without confirmation |
| `--trust-tools <TOOL_NAMES>` | Trust only specific tools (comma-separated) |
| `--no-interactive` | Run without expecting user input (for piping) |
| `-l, --list-sessions` | List all saved chat sessions for current directory |
| `--list-models` | List available models and exit |
| `-f, --format <FORMAT>` | Output format: `plain`, `json`, `json-pretty` |
| `-d, --delete-session <ID>` | Delete a saved chat session by ID |
| `--session-source <v1\|v2>` | Target v1 or v2 store for delete |
| `-w, --wrap <WRAP>` | Line wrapping: `always`, `never`, `auto` |
| `--require-mcp-startup` | Exit code 3 if any MCP server fails to start |
| `--tui` | Use new terminal UI |
| `--legacy-ui` | Use legacy terminal UI |

### Usage Patterns

```bash
# Simple question (non-interactive, for piping)
echo "Explain Docker" | kiro-cli chat --no-interactive --model claude-haiku-4.5 --trust-all-tools --wrap never

# Interactive chat with specific model
kiro-cli chat --model claude-opus-4.6

# Resume previous conversation
kiro-cli chat --resume

# Use a specific agent
kiro-cli chat --agent "AWS Expert"

# Trust specific tools only
kiro-cli chat --trust-tools=fs_read,fs_write,execute_bash

# List models as JSON (for programmatic use)
kiro-cli chat --list-models --format json
```

### Key Flags for Hermes Integration

For non-interactive subprocess usage (what kiro-openai-wrapper uses):
```bash
kiro-cli chat --no-interactive --model <MODEL> --trust-all-tools --wrap never
```

- `--no-interactive`: Essential — prevents waiting for stdin after first message
- `--trust-all-tools`: Prevents tool approval prompts that would block
- `--wrap never`: Raw output without terminal width wrapping

---

## MCP

**Model Context Protocol server management.**

### Subcommands

| Command | Description |
|---------|-------------|
| `mcp add` | Add or replace a configured server |
| `mcp remove` | Remove a server from configuration |
| `mcp list` | List configured servers |
| `mcp import` | Import server config from another file |
| `mcp status` | Get status of a configured server |

### `mcp add` Options

| Flag | Description |
|------|-------------|
| `--name <NAME>` | Server name (optional with registry) |
| `--scope <SCOPE>` | `default`, `workspace`, or `global` |
| `--command <COMMAND>` | Launch command (stdio servers) |
| `--url <URL>` | URL for HTTP-based servers |
| `--args <ARGS>` | Arguments (multiple flags, comma-separated, or JSON array) |
| `--agent <AGENT>` | Agent to add server to |
| `--env <ENV>` | Environment variables |
| `--timeout <TIMEOUT>` | Launch timeout in milliseconds |
| `--disabled` | Start disabled |
| `--force` | Overwrite existing server |

### Currently Configured MCP Servers

**Active (enabled):**
| Server | Transport | Description |
|--------|-----------|-------------|
| Context7 | npx | Library documentation lookup |
| arxiv | uvx | Academic paper search/download |
| playwright | npx | Browser automation |
| steelmind | npx | Structured thinking (think/verify) |
| tavily-remote | npx (remote) | Web search, extract, crawl, research |

**Disabled:**
| Server | Transport | Description |
|--------|-----------|-------------|
| Artiforge | HTTP | Development task planning |
| atlassian | npx (remote) | Jira/Confluence |
| code-reasoning | npx | Code reasoning |
| fetch | uvx | URL fetching |
| firecrawl-mcp | npx | Web scraping |
| jupyter-editor | uvx | Jupyter notebook editing |
| mcp-icd10 | docker | Medical coding |
| memory | npx | Knowledge graph memory |
| mermaid-mcp | SSE | Diagram rendering |
| obsidian | npx | Obsidian vault access |
| openrouter | npx | Multi-model routing |
| sequentialthinking | docker | Sequential reasoning |

### MCP Config Location

- **Global:** `~/.kiro/settings/mcp.json`
- **Workspace:** `.kiro/settings/mcp.json` (in project root)
- **Per-agent:** Configured via `--agent` flag

### Config Format (kiro-cli)

```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "@package/name@latest"],
      "env": { "API_KEY": "..." },
      "disabled": false,
      "autoApprove": ["tool1", "tool2"],
      "disabledTools": ["tool3"]
    }
  }
}
```

---

## Agent Management

### Subcommands

| Command | Description |
|---------|-------------|
| `agent list` | List available agents |
| `agent create [NAME]` | Create an agent config |
| `agent edit` | Edit an existing agent |
| `agent validate` | Validate a config |
| `agent migrate` | Migrate profiles to agents |
| `agent set-default` | Set default agent |

### Agent Locations

- **Built-in:** `kiro_default`, `kiro_help`, `kiro_planner`
- **Global:** `~/.kiro/agents/`
- **Workspace:** `.kiro/agents/` (in project root)

### `agent create` Options

| Flag | Description |
|------|-------------|
| `-d, --directory <DIR>` | Save location (default: global) |
| `-f, --from <AGENT>` | Clone from existing agent |

---

## Available Models

| Model | Context Window | Rate | Description |
|-------|---------------|------|-------------|
| `auto` | 1,000,000 | 1.00x | Task-optimized routing (default) |
| `claude-opus-4.6` | 1,000,000 | 2.20x | Best quality |
| `claude-sonnet-4.6` | 1,000,000 | 1.30x | Latest Sonnet, 1M context |
| `claude-opus-4.5` | 200,000 | 2.20x | Previous Opus |
| `claude-sonnet-4.5` | 200,000 | 1.30x | Previous Sonnet |
| `claude-sonnet-4` | 200,000 | 1.30x | Hybrid reasoning |
| `claude-haiku-4.5` | 200,000 | 0.40x | Fastest/cheapest |
| `deepseek-3.2` | 164,000 | 0.25x | Experimental DeepSeek |
| `minimax-m2.5` | 196,000 | 0.25x | MiniMax M2.5 |
| `minimax-m2.1` | 196,000 | 0.15x | Experimental MiniMax |
| `glm-5` | 200,000 | 0.50x | GLM-5 |
| `qwen3-coder-next` | 256,000 | 0.05x | Experimental Qwen3 Coder |

**Key insight:** `claude-sonnet-4.6` and `claude-opus-4.6` have **1M token context windows** — much larger than previously documented in the wrapper (200K). The wrapper should be updated.

---

## Available Tools (Built-in to kiro-cli)

kiro-cli has **57 built-in tools** plus MCP tools:

### File System
- `fs_read` — Read files
- `fs_write` — Write/create files
- `glob` — File pattern matching
- `grep` — Text search in files

### Execution
- `execute_bash` — Run shell commands
- `code` — Code execution

### Browser (via Playwright MCP)
- `browser_click`, `browser_close`, `browser_console_messages`
- `browser_drag`, `browser_drop`, `browser_evaluate`
- `browser_file_upload`, `browser_fill_form`, `browser_handle_dialog`
- `browser_hover`, `browser_navigate`, `browser_navigate_back`
- `browser_network_request`, `browser_network_requests`
- `browser_press_key`, `browser_resize`, `browser_run_code_unsafe`
- `browser_select_option`, `browser_snapshot`, `browser_tabs`
- `browser_take_screenshot`, `browser_type`, `browser_wait_for`

### Research & Web
- `web_search` — Web search
- `web_fetch` — Fetch URL content
- `tavily_search`, `tavily_crawl`, `tavily_extract`, `tavily_map`, `tavily_research`

### Academic
- `search_papers`, `download_paper`, `list_papers`, `read_paper`
- `get_abstract`, `semantic_search`, `reindex`
- `citation_graph`, `check_alerts`, `watch_topic`

### Documentation
- `resolvelibraryid` — Context7 library resolution
- `querydocs` — Context7 documentation query

### Reasoning
- `think` — Structured thinking (steelmind)
- `verify` — Critical self-assessment (steelmind)
- `thinking` — Extended reasoning

### Agent & Session
- `use_subagent` — Delegate to sub-agents
- `session` — Session management
- `knowledge` — Knowledge base access
- `introspect` — Self-introspection
- `todo_list` — Task management
- `use_aws` — AWS operations

### Utility
- `report_issue` — Report issues
- `dummy` — Test/placeholder tool

---

## Settings

### Key Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `chat.defaultModel` | `claude-opus-4.6` | Default model |
| `chat.enableCheckpoint` | `true` | Enable checkpoints |
| `chat.enableContextUsageIndicator` | `true` | Show context usage |
| `chat.enableKnowledge` | `true` | Enable knowledge base |
| `chat.enableTangentMode` | `true` | Enable tangent mode |
| `chat.enableThinking` | `true` | Enable thinking/reasoning |
| `chat.enableTodoList` | `true` | Enable todo list |
| `chat.greeting.enabled` | `false` | Disable greeting |
| `telemetry.enabled` | `false` | Disable telemetry |

### Setting Commands

```bash
# List all settings
kiro-cli settings list

# Set a value
kiro-cli settings chat.defaultModel "claude-sonnet-4.6"

# Set workspace-level
kiro-cli settings --workspace chat.defaultModel "claude-haiku-4.5"

# Delete a setting
kiro-cli settings -d chat.greeting.enabled

# Open settings file
kiro-cli settings open
```

---

## MCP Harness Recommendation

### The Question: kiro-cli MCP vs Hermes MCP?

Both kiro-cli and Hermes Agent have full MCP client implementations. Here's the comparison:

### kiro-cli MCP Harness

**Pros:**
- Already configured with your servers (Context7, arxiv, playwright, steelmind, tavily)
- Managed by kiro-cli's lifecycle (auto-start, auto-restart)
- `autoApprove` lists already configured
- Integrated with kiro-cli's tool routing and model context
- Zero additional setup — just works when you use kiro-cli
- Supports `disabledTools` for fine-grained control
- Handles auth (OAuth, API keys) natively

**Cons:**
- Tools are only available during kiro-cli subprocess execution
- No persistent MCP connections between calls (each `--no-interactive` invocation may restart servers)
- Can't share MCP state with Hermes's memory/skill system
- Limited control over tool result formatting

### Hermes Agent MCP Harness

**Pros:**
- Persistent connections — MCP servers stay running across the session
- Deep integration with Hermes's tool registry, memory, and skill system
- Tool interception hooks (pre/post execution)
- Parallel tool execution with proper provenance tracking
- MCP tool results flow into Hermes's trajectory/training pipeline
- Sampling handler — MCP servers can request LLM completions back
- OAuth flow support with browser-based auth
- Resource and prompt discovery (not just tools)

**Cons:**
- Requires separate configuration (`mcp_servers` in Hermes config.yaml)
- Needs the `mcp` Python package installed
- Separate lifecycle management from kiro-cli

### Recommendation: **Use BOTH — Layered Approach**

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes Agent                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Hermes MCP Harness (persistent, integrated)     │    │
│  │  • Memory server (knowledge graph)               │    │
│  │  • Custom project-specific servers               │    │
│  │  • Servers needing persistent state              │    │
│  └─────────────────────────────────────────────────┘    │
│                         │                                │
│  ┌─────────────────────▼───────────────────────────┐    │
│  │  kiro-cli (subprocess LLM backbone)              │    │
│  │  ┌─────────────────────────────────────────┐    │    │
│  │  │  kiro-cli MCP Harness (per-invocation)   │    │    │
│  │  │  • Context7 (stateless doc lookup)       │    │    │
│  │  │  • arxiv (stateless search)              │    │    │
│  │  │  • tavily (stateless web search)         │    │    │
│  │  │  • playwright (browser automation)       │    │    │
│  │  │  • steelmind (reasoning)                 │    │    │
│  │  └─────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Rule of thumb:**
- **Stateless, lookup-oriented servers** → Let kiro-cli handle them (Context7, arxiv, tavily, web search). They don't need persistent connections.
- **Stateful, session-oriented servers** → Use Hermes's harness (memory, project-specific tools, anything that accumulates state across turns).
- **Browser automation** → kiro-cli's playwright is fine for one-shot tasks; Hermes's harness is better for multi-step browser workflows.

**For your local-only setup:** Since kiro-cli already has all your MCP servers configured and working, let kiro-cli handle them. Hermes Agent calls kiro-cli, which automatically loads its MCP servers. This means:
- Zero duplicate configuration
- kiro-cli manages server lifecycle
- All 57+ tools available to the model during inference
- Hermes focuses on what it does best: memory, skills, multi-turn orchestration

If you later need persistent MCP state (e.g., a knowledge graph that accumulates across sessions), add those specific servers to Hermes's config.

---

## ACP (Agent Client Protocol)

```bash
kiro-cli acp [OPTIONS]
```

| Flag | Description |
|------|-------------|
| `--agent <AGENT>` | Agent for first session |
| `--model <MODEL>` | Model for first session |
| `-a, --trust-all-tools` | Auto-approve all tools |
| `--trust-tools <TOOLS>` | Trust specific tools |

ACP exposes kiro-cli as an agent that other tools can communicate with via the Agent Client Protocol. This is how IDE integrations (VS Code, JetBrains) communicate with kiro-cli.

---

## Other Commands

### translate (NL → Shell)
```bash
kiro-cli translate "find all python files modified today"
# Outputs: find . -name "*.py" -mtime 0
```

### inline (Shell Completions)
```bash
kiro-cli inline enable    # Enable inline completions
kiro-cli inline disable   # Disable
kiro-cli inline status    # Check status
```

### init (Shell Integration)
```bash
# Add to .zshrc:
eval "$(kiro-cli init zsh post)"
```

### doctor (Diagnostics)
```bash
kiro-cli doctor  # Check for common issues
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KIRO_CLI_PATH` | Override binary location |
| (MCP server env vars) | Passed to MCP servers via config |

---

## File Locations

| Path | Purpose |
|------|---------|
| `~/.local/bin/kiro-cli` | Binary |
| `~/.kiro/settings/mcp.json` | Global MCP config |
| `~/.kiro/agents/` | Global agent configs |
| `.kiro/settings/mcp.json` | Workspace MCP config |
| `.kiro/agents/` | Workspace agent configs |

---

*Document generated by researching kiro-cli v2.2.2 on macOS, May 17, 2026.*
