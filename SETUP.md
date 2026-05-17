# Hermes Agent + kiro-cli — Team Setup Guide

Get Hermes Agent running locally with kiro-cli as the LLM backbone. Takes ~5 minutes.

---

## Prerequisites

- **macOS** (tested on Apple Silicon)
- **kiro-cli** installed at `~/.local/bin/kiro-cli` (comes with Kiro IDE)
- **Python 3.11+** (`python3 --version`)
- **Logged in:** `kiro-cli whoami` should show your identity

---

## Quick Setup (Copy-Paste)

```bash
# 1. Clone the repo
git clone https://github.com/stabgan/hermes-agent.git ~/hermes-agent
cd ~/hermes-agent
git checkout feat/kiro-cli-local-integration

# 2. Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Install the wrapper dependencies
pip install fastapi uvicorn pydantic

# 4. Copy config to ~/.hermes/
mkdir -p ~/.hermes
cp kiro-local-config.yaml ~/.hermes/config.yaml

# 5. Create your SOUL.md (personality)
cat > ~/.hermes/SOUL.md << 'EOF'
# Identity

You are Hermes, a self-improving AI agent running locally via kiro-cli.
You learn from every interaction, create reusable skills, and maintain
persistent memory. You are direct, capable, and continuously improving.
EOF

# 6. Install MCP servers into kiro-cli (web search, browser, arxiv, docs, reasoning)
chmod +x setup-mcp.sh && ./setup-mcp.sh

# 7. Install the Kiro IDE skill (optional — lets Kiro delegate to Hermes)
cp skills/autonomous-ai-agents/kiro-cli/KIRO_SKILL.md ~/.kiro/skills/hermes-agent.md

echo "✅ Setup complete!"
```

---

## Running Hermes

You need two terminals (or use the launcher script):

### Terminal 1 — Start the wrapper

```bash
cd ~/hermes-agent
source .venv/bin/activate
python kiro-openai-wrapper/main.py
```

You should see: `Uvicorn running on http://127.0.0.1:8000`

### Terminal 2 — Run Hermes

```bash
cd ~/hermes-agent
source .venv/bin/activate

# Interactive mode
hermes --provider custom --model claude-opus-4.6 --yolo

# Or one-shot mode
hermes -z "Your task here" --provider custom --model claude-opus-4.6 --yolo
```

### One-Liner Launcher (both in one)

```bash
cd ~/hermes-agent && source .venv/bin/activate && \
  python kiro-openai-wrapper/main.py & sleep 2 && \
  hermes --provider custom --model claude-opus-4.6 --yolo
```

---

## Using from Kiro IDE

After step 6 above, you can delegate tasks to Hermes from Kiro chat:

1. Type `#hermes-agent` in Kiro chat to load the skill
2. Ask Kiro to delegate: "Use Hermes to research X and create a report"
3. Kiro will run Hermes via the terminal tool

---

## What You Get

| Feature | Description |
|---------|-------------|
| **Claude Opus 4.6** | 1M token context, best reasoning |
| **57 tools** | File I/O, bash, web search, browser, arxiv, docs |
| **5 MCP servers** | Context7, arxiv, playwright, steelmind, tavily |
| **Persistent memory** | Remembers across sessions |
| **Skills** | Auto-creates reusable procedures |
| **Goals** | Multi-step task tracking |
| **Subagents** | 8 specialized roles (researcher, developer, reviewer...) |

---

## Available Models

| Model | Context | Best For |
|-------|---------|----------|
| `claude-opus-4.6` | 1M | Complex reasoning (default) |
| `claude-sonnet-4.6` | 1M | Balanced speed/quality |
| `claude-haiku-4.5` | 200K | Quick tasks |
| `deepseek-3.2` | 164K | Cheap code generation |
| `qwen3-coder-next` | 256K | Cheapest option |

Switch models: `hermes -z "task" --model claude-haiku-4.5 --provider custom --yolo`

---

## Key Commands

```bash
# Interactive chat
hermes --provider custom --model claude-opus-4.6 --yolo

# One-shot task
hermes -z "Fix the bug in main.py" --provider custom --model claude-opus-4.6 --yolo

# Goal-driven (multi-step)
hermes -z "/goal Build a REST API with tests" --provider custom --model claude-opus-4.6 --yolo

# Resume last session
hermes --resume --provider custom --model claude-opus-4.6 --yolo

# Check status
hermes status
```

---

## Context Window & Session Management

**You have 1M tokens of context** with Claude Opus 4.6. That's roughly 750K words or ~3000 pages of text in a single conversation.

Hermes auto-compresses at 50% (500K tokens) so you'll never hit the wall unexpectedly. But you can also manage it manually:

### Slash Commands (inside interactive chat)

| Command | What It Does |
|---------|-------------|
| `/new` | Start fresh session (new ID, clean history, CLI stays open) |
| `/clear` | Wipe terminal + start new session |
| `/compress` | Manually compress context when things get long |
| `/status` | Show token usage, model, session info |
| `/save` | Save conversation to disk without ending |
| `/history` | Print current conversation inline |
| `/goal <task>` | Set a persistent goal that auto-continues until done |
| `/steer <note>` | Nudge direction mid-task without interrupting |
| `/copy` | Copy last response to clipboard |

### Session Lifecycle

```
Start → Work → (auto-compress at 500K tokens) → Keep working → /new when done
                                                              → /compress to reclaim space
                                                              → hermes --resume to continue later
```

### Practical Tips

- **Long sessions:** Hermes auto-compresses. You don't need to manage context manually.
- **Fresh start:** Type `/new` inside chat, or just restart hermes without `--resume`.
- **Save progress:** Memory persists automatically. `/new` starts fresh chat but memory stays.
- **Resume later:** `hermes --resume` picks up where you left off (full history).
- **Multiple projects:** Each directory gets its own session history. `cd` to the project first.

---

## Project Structure

```
hermes-agent/
├── kiro-openai-wrapper/       # OpenAI-compatible wrapper around kiro-cli
│   ├── main.py                # FastAPI server (start this first)
│   └── api.py                 # The wrapper logic
├── agent/                     # Our custom modules
│   ├── lint_guard.py          # Auto-validates file edits
│   ├── memory_blocks.py       # Structured persistent memory
│   ├── microcompact.py        # LLM-free context stripping
│   ├── output_truncation.py   # Smart output truncation
│   ├── prompt_cache_stable.py # KV cache-friendly prompt ordering
│   └── role_profiles.py       # Specialized subagent roles
├── providers/
│   └── kiro_cli.py            # Native kiro-cli provider
├── skills/autonomous-ai-agents/kiro-cli/
│   ├── SKILL.md               # Hermes skill for using kiro-cli
│   └── KIRO_SKILL.md          # Kiro IDE skill for using Hermes
├── tests/
│   ├── test_integrations.py   # 56 unit tests
│   └── test_deep_integrations.py  # 219 deep tests
├── kiro-local-config.yaml     # Config template (copy to ~/.hermes/)
├── HERMES_GUIDE.md            # Full usage guide
├── KIRO_CLI_REFERENCE.md      # Complete kiro-cli documentation
└── SETUP.md                   # This file
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `hermes: command not found` | `source ~/hermes-agent/.venv/bin/activate` |
| "No LLM provider configured" | Start the wrapper first: `python kiro-openai-wrapper/main.py` |
| Empty responses | Check wrapper is running: `curl http://localhost:8000/v1/models` |
| `kiro-cli: command not found` | Install Kiro IDE or check `~/.local/bin/kiro-cli` |
| Auth expired | Run `kiro-cli login` |
| Slow responses | Opus thinks deeply. Use `--model claude-haiku-4.5` for speed |
| Port 8000 in use | Kill existing: `lsof -ti:8000 | xargs kill` |

---

## Updating

```bash
cd ~/hermes-agent
git pull origin feat/kiro-cli-local-integration
source .venv/bin/activate
pip install -e .
```

---

## Running Tests

```bash
cd ~/hermes-agent
source .venv/bin/activate
python -m pytest tests/test_integrations.py tests/test_deep_integrations.py -o "addopts=" -q
# Expected: 275 passed
```
