# Hermes Agent — Complete Guide for Local kiro-cli Deployment

## Quick Answers

### Should `prompt_caching` be false?

**Yes, keep it false.** Here's why:

Anthropic's prompt caching requires the native Messages API with specific `cache_control` breakpoints injected into the request. Since we're routing through the OpenAI-compatible chat completions API (kiro-openai-wrapper), the caching headers never reach Anthropic's infrastructure. kiro-cli itself handles its own internal caching — you get the benefit without configuring it in Hermes.

If you ever switch to using Anthropic's API directly (not through kiro-cli), then enable it.

### Should `telemetry` be false?

**Yes, keep it false.** Hermes's telemetry would attempt to send usage data to NousResearch's servers. Since your deployment is local-only and privacy-focused, there's no reason to enable it. All your session data, memory, and skills stay on your machine.

---

## End-to-End Features of Hermes Agent

### 1. Persistent Memory (`/memory`)

Hermes remembers across sessions. Two files in `~/.hermes/`:
- **MEMORY.md** — Agent's knowledge base (projects, decisions, patterns learned)
- **USER.md** — Your preferences, communication style, context

**How to leverage:**
```
/memory                    # View current memory
/memory add "Prefers TypeScript over JavaScript"
/memory search "database"  # Search past memories
```

The agent also auto-saves memories via periodic "nudges" — it'll ask itself "what should I remember from this conversation?"

### 2. Skills System (`/skills`)

Skills are reusable procedures the agent creates after solving complex tasks.

**How to leverage:**
```
/skills                    # List all skills
/skills view <name>        # Read a skill's instructions
/skills create             # Manually trigger skill creation
```

After a complex task, the agent may autonomously create a skill. Next time you ask for something similar, it reads the skill first — getting better each time.

**Bundled skills include:** architecture-diagram, code-review, test-driven-development, systematic-debugging, writing-plans, subagent-driven-development, and 100+ more.

### 3. Goals (`/goal`)

Set a persistent objective that the agent works toward across multiple turns.

**How to leverage:**
```
/goal Build a REST API with authentication using FastAPI
```

The agent will:
1. Break the goal into subtasks
2. Work through them using tools
3. Self-evaluate progress after each turn
4. Continue until the goal is complete or you interrupt

### 4. Todo List (`/todo`)

In-session task tracking that the agent uses to organize multi-step work.

```
/todo                      # View current tasks
/todo add "Write tests"    # Add a task
/todo done 1               # Mark task complete
```

The agent uses this internally during complex goals to track progress.

### 5. Subagent Delegation (`delegate_task`)

Spawn child agents for parallel or specialized work:
- Each subagent gets its own context window
- Can have restricted tool access
- Results flow back to the parent agent

### 6. Session Management

```
hermes --resume            # Resume last conversation
hermes --resume-id <id>    # Resume specific session
/session search "auth"     # Search past sessions
/new                       # Start fresh conversation
```

### 7. Cron Scheduling (`hermes cron`)

Schedule recurring tasks:
```bash
hermes cron add --name "daily-summary" --schedule "0 9 * * *" \
  --prompt "Summarize what I worked on yesterday"
```

### 8. Gateway (Multi-Platform)

Run Hermes on Telegram, Discord, Slack, WhatsApp, Signal, Email — all from one instance:
```bash
hermes gateway start
```

### 9. Context Compression

When conversations get long, Hermes automatically compresses old messages while preserving key information. With 1M context on Opus 4.6, this rarely triggers — but it's there for marathon sessions.

### 10. Checkpoints

```
/checkpoint init           # Enable checkpoints in current directory
/checkpoint list           # View saved states
/checkpoint restore <id>   # Roll back file changes
```

### 11. MCP Integration

All kiro-cli's MCP tools (Context7, arxiv, playwright, steelmind, tavily) are available automatically during inference. The agent can search documentation, browse the web, read papers, and reason structurally.

### 12. Kanban (Multi-Agent Orchestration)

```
/kanban                    # View task board
/kanban add "Implement auth module"
```

For complex projects, the kanban system coordinates multiple subagents working on different tasks.

---

## Best Practices

### 1. Start with a Goal, Not a Question

Instead of: "How should I structure my API?"
Use: `/goal Design and implement a REST API for user management with JWT auth`

Goals trigger the full agent loop — tool use, file creation, testing, iteration.

### 2. Let Memory Accumulate

Don't start fresh sessions for the same project. Use `--resume` to continue where you left off. The agent's memory compounds — it remembers your preferences, project structure, and past decisions.

### 3. Use the Right Model for the Task

```bash
# Complex architecture/planning → Opus (default)
hermes -z "/goal ..." --model claude-opus-4.6

# Quick questions/simple edits → Haiku (faster, cheaper)
hermes -z "Fix the typo in main.py" --model claude-haiku-4.5
```

### 4. Trust Tools Selectively

`--yolo` trusts everything. For sensitive work:
```bash
hermes --trust-tools=fs_read,grep,execute_bash  # Read-only + shell
```

### 5. Create Skills for Recurring Workflows

After the agent solves something complex, tell it:
```
Create a skill from what you just did so you can do it faster next time.
```

### 6. Use Subagents for Parallel Work

For large tasks:
```
Break this into 3 subtasks and delegate each to a subagent.
```

### 7. Leverage the 1M Context Window

With Opus 4.6's 1M token context, you can:
- Paste entire files without worrying about truncation
- Have very long conversations without compression
- Include full error logs, stack traces, documentation

### 8. Background Processing

Use cron for:
- Daily code review of recent commits
- Weekly dependency update checks
- Automated test runs with analysis

---

## Architecture for Your Setup

```
┌─────────────────────────────────────────────────────────────┐
│                         YOU                                   │
│              (CLI / TUI / Gateway)                            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    HERMES AGENT                               │
│  ┌──────────┐ ┌────────┐ ┌───────┐ ┌──────┐ ┌───────────┐ │
│  │ Memory   │ │ Skills │ │ Goals │ │ Todo │ │ Subagents │ │
│  │ (persist)│ │ (learn)│ │(track)│ │(plan)│ │ (parallel)│ │
│  └──────────┘ └────────┘ └───────┘ └──────┘ └───────────┘ │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Context Engine                           │   │
│  │  microcompact → compression → cache-stable prompts   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │ OpenAI-compatible API
┌──────────────────────────▼──────────────────────────────────┐
│              kiro-openai-wrapper (localhost:8000)             │
└──────────────────────────┬──────────────────────────────────┘
                           │ subprocess
┌──────────────────────────▼──────────────────────────────────┐
│                      kiro-cli                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Claude Opus 4.6 (1M context, 32K output)           │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  MCP Servers (auto-loaded)                          │    │
│  │  • Context7 (library docs)                          │    │
│  │  • arxiv (papers)                                   │    │
│  │  • playwright (browser)                             │    │
│  │  • steelmind (reasoning)                            │    │
│  │  • tavily (web search)                              │    │
│  └─────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  57 Built-in Tools                                  │    │
│  │  fs_read, fs_write, execute_bash, grep, glob...     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Integrations from Other Projects (Recommended)

Based on the research in `INTEGRATION_RESEARCH.md`, here are the highest-value additions:

### Already Implemented (in your fork)

| Feature | Source | File |
|---------|--------|------|
| Microcompact (LLM-free context stripping) | Issue #525 | `agent/microcompact.py` |
| Cache-stable prompt ordering | Issue #4319 | `agent/prompt_cache_stable.py` |
| Native kiro-cli provider | PRs #26960, #26940 | `providers/kiro_cli.py` |

### Recommended Next (Tier 1 — Quick Wins)

| Feature | From | What It Does |
|---------|------|-------------|
| **Lint-on-Edit Guard** | SWE-agent | Auto-reject file edits that introduce syntax errors |
| **Role-Based Subagents** | CrewAI | Give delegate_task specialized roles (researcher/developer/reviewer) |
| **Structured Memory Blocks** | Letta/MemGPT | Always-in-context labeled memory sections |
| **Working Memory Scratchpad** | Letta/MemGPT | Survives compression, tracks current task state |

### Future (Tier 2-3)

| Feature | From | What It Does |
|---------|------|-------------|
| PageRank Repo Map | Aider | Auto-select relevant code context via tree-sitter |
| Change Sandbox | Plandex | Review AI changes before applying to disk |
| DAG Task Planning | Devon | Tasks with dependencies and validation gates |
| Archival Memory | Letta | Semantic vector search over long-term knowledge |

---

## Daily Workflow

```bash
# Morning: Start wrapper + hermes
cd ~/Development/hermes
source hermes-agent/.venv/bin/activate
python kiro-openai-wrapper/main.py &   # Background
hermes --yolo                           # Interactive session

# In session:
/goal <today's main task>              # Set objective
# ... work with the agent ...
/memory                                 # Check what it learned
/skills                                 # See if new skills were created

# Resume later:
hermes --resume                         # Pick up where you left off
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "No LLM provider configured" | Ensure wrapper is running on localhost:8000 |
| Empty responses | Check `curl http://localhost:8000/v1/models` returns data |
| Slow responses | kiro-cli is processing — Opus 4.6 thinks deeply |
| Memory not saving | Check `~/.hermes/MEMORY.md` exists and is writable |
| Tools not working | Use `--yolo` flag or `--trust-tools=<list>` |
