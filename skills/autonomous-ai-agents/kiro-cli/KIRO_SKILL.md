---
inclusion: manual
---

# Hermes Agent — Kiro Subagent Skill

Use Hermes Agent as a powerful subagent from Kiro. Hermes provides persistent memory, autonomous skill creation, multi-platform presence, and a self-improving learning loop — capabilities that complement Kiro's coding focus.

## When to Use Hermes

- **Persistent memory across sessions** — Hermes remembers projects, preferences, and past decisions
- **Complex multi-step goals** — Hermes tracks progress with /goal and /todo
- **Research tasks** — Hermes has web search, arxiv, browser automation via its MCP tools
- **Background automation** — Hermes can run cron jobs, scheduled tasks
- **Multi-platform delivery** — Send results to Telegram, Discord, Slack, Email
- **Self-improving workflows** — Hermes creates skills from experience

## Setup

Hermes Agent is installed at `~/Development/hermes/hermes-agent` with a virtual environment at `.venv/`.

```bash
# Activate and run
source ~/Development/hermes/hermes-agent/.venv/bin/activate
hermes --provider custom --model claude-opus-4.6 --yolo
```

## Delegation Patterns

### Pattern 1: One-Shot Task (Non-Interactive)

Use `-z` flag for a single prompt that runs to completion:

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "YOUR TASK HERE" --provider custom --model claude-opus-4.6 --yolo
```

Example:
```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "/goal Research the latest FastAPI security best practices and create a checklist at ./SECURITY_CHECKLIST.md" --provider custom --model claude-opus-4.6 --yolo
```

### Pattern 2: Goal-Driven Execution

For complex multi-step work, use `/goal` prefix:

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "/goal Build a complete REST API with auth, tests, and documentation in ./api/" --provider custom --model claude-opus-4.6 --yolo
```

Hermes will:
1. Break the goal into subtasks
2. Execute each using tools (file write, bash, etc.)
3. Self-evaluate progress
4. Continue until complete

### Pattern 3: Research & Summarize

Hermes has web search, arxiv, and browser tools via kiro-cli:

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "Research the top 5 Python RL libraries in 2025, compare their features, and write a comparison table to ./RL_COMPARISON.md" --provider custom --model claude-opus-4.6 --yolo
```

### Pattern 4: Code Review with Memory

Hermes remembers past reviews and project context:

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "Review all Python files in src/ for security issues, code quality, and test coverage gaps. Write findings to ./CODE_REVIEW.md" --provider custom --model claude-opus-4.6 --yolo
```

### Pattern 5: Resume Previous Work

Hermes persists sessions. Resume where you left off:

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes --resume --provider custom --model claude-opus-4.6 --yolo
```

### Pattern 6: Delegate to Hermes Subagents

Hermes can spawn its own specialized subagents (researcher, developer, reviewer, tester, debugger):

```bash
source ~/Development/hermes/hermes-agent/.venv/bin/activate && hermes -z "Delegate to a researcher subagent: find all open issues in NousResearch/hermes-agent related to memory persistence. Then delegate to a planner subagent: create an implementation plan." --provider custom --model claude-opus-4.6 --yolo
```

## Key Hermes Commands

| Command | What It Does |
|---------|-------------|
| `-z "prompt"` | Single prompt, runs to completion |
| `--resume` | Resume last session |
| `--yolo` | Trust all tools (no approval prompts) |
| `--provider custom --model claude-opus-4.6` | Use kiro-cli backend with Opus |
| `/goal <task>` | Set a persistent goal (prefix in -z) |
| `/todo` | View task list |
| `/memory` | View persistent memory |
| `/skills` | View learned skills |

## Hermes Features Available

| Feature | Description |
|---------|-------------|
| **Persistent Memory** | Remembers across sessions (~/.hermes/MEMORY.md, USER.md) |
| **Skills System** | Creates reusable procedures from experience |
| **Goals** | Tracks multi-step objectives to completion |
| **Subagents** | Spawns specialized child agents (researcher, developer, reviewer, tester, debugger, planner, documenter, refactorer) |
| **Session Search** | Full-text search over all past conversations |
| **Checkpoints** | Rollback file changes |
| **Cron** | Schedule recurring tasks |

## Architecture

```
Kiro IDE (you are here)
  │
  ├── Direct coding (Kiro's native tools)
  │
  └── Delegate to Hermes (via terminal)
        │
        └── Hermes Agent
              ├── Memory (persistent across sessions)
              ├── Skills (learned procedures)
              ├── Goals (multi-step tracking)
              ├── Subagents (specialized delegation)
              └── kiro-cli backend
                    ├── Claude Opus 4.6 (1M context)
                    └── MCP servers (web, browser, arxiv, docs, reasoning)
```

## When to Use Kiro vs Hermes

| Task | Use Kiro Directly | Delegate to Hermes |
|------|-------------------|-------------------|
| Quick file edits | ✅ | |
| Single-file coding | ✅ | |
| Spec-driven development | ✅ | |
| Multi-step goals | | ✅ |
| Research requiring web/papers | | ✅ |
| Tasks needing persistent memory | | ✅ |
| Background/scheduled work | | ✅ |
| Multi-platform delivery | | ✅ |
| Self-improving workflows | | ✅ |
| Code review with project history | | ✅ |

## Important Notes

1. **Always activate the venv first** — Hermes is installed in `~/Development/hermes/hermes-agent/.venv/`
2. **The wrapper must be running** for Hermes to work — start it with `python ~/Development/hermes/kiro-openai-wrapper/main.py` in a background terminal
3. **Hermes writes to the current directory** — `cd` to the project before running
4. **Use `--yolo` for automation** — otherwise Hermes will prompt for tool approval
5. **Hermes accumulates memory** — the more you use it on a project, the better it gets
