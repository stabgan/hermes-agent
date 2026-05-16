# Integration Research: Open Source AI Agent Projects → Hermes Agent

**Goal:** Identify practical, implementable patterns from leading open-source AI agent projects that can be integrated with Hermes Agent for a LOCAL-ONLY deployment using kiro-cli as the LLM backbone.

**Date:** 2025-05-17  
**Hermes Version:** v0.14.x  
**Target Architecture:** kiro-cli provider → Claude Opus 4.6 (1M context, local inference)

---

## Table of Contents

1. [Aider — PageRank Repo Map](#1-aider--pagerank-repo-map)
2. [OpenHands — Event-Driven Agent Architecture](#2-openhands--event-driven-agent-architecture)
3. [Goose — Extension System & Custom Distributions](#3-goose--extension-system--custom-distributions)
4. [Devon — Planning & Task Decomposition](#4-devon--planning--task-decomposition)
5. [Plandex — Version-Controlled Plans](#5-plandex--version-controlled-plans)
6. [Letta/MemGPT — Tiered Memory Architecture](#6-lettamemgpt--tiered-memory-architecture)
7. [CrewAI — Multi-Agent Orchestration](#7-crewai--multi-agent-orchestration)
8. [SWE-agent — Agent-Computer Interfaces](#8-swe-agent--agent-computer-interfaces)
9. [Priority Integration Roadmap](#9-priority-integration-roadmap)

---

## 1. Aider — PageRank Repo Map

**GitHub:** [Aider-AI/aider](https://github.com/Aider-AI/aider) | ~33k stars | Very Active (daily commits)  
**Language:** Python | **License:** Apache-2.0

### What It Does

Aider's killer feature is its **tree-sitter-based repo map** that automatically selects relevant context from a codebase. It:

1. Parses every file with tree-sitter to extract "tags" (function defs, class defs, references)
2. Builds a directed graph of symbol relationships (who-calls-whom)
3. Runs PageRank on the graph to rank symbols by importance
4. Given the user's current chat files, selects the most relevant OTHER files/symbols to include as context
5. Fits the ranked context into the available token budget

### Key Architecture (from `aider/repomap.py`)

```
User's chat files → tree-sitter parse → tag extraction → 
  reference graph → PageRank scoring → ranked symbol list →
  token-budget fitting → context string for LLM
```

The graph edges connect:
- A file that **defines** a symbol → files that **reference** that symbol
- Personalization: files the user is actively editing get boosted

### What to Extract for Hermes

**Component: `RepoMapTool` — Automatic Context Selection**

Hermes already has `search_files` and `read_file` tools, but the agent must manually decide what context to include. Aider's approach is *automatic* — it pre-computes what's relevant.

**Implementation Plan:**
1. Create `tools/repo_map.py` — a new tool that builds a tree-sitter graph on demand
2. Hook into `agent/context_engine.py` — inject repo map context before each LLM call
3. Use the existing `subdirectory_hints.py` pattern as the injection point

**Specific Code to Adapt:**
- `aider/repomap.py` — The core PageRank + tree-sitter logic (~800 lines)
- `aider/repo_map_tags.py` — Tag extraction queries per language
- The "ranked tags" algorithm that fits context into a token budget

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `agent/context_engine.py` | Inject repo map as pre-turn context (like memory prefetch) |
| `agent/subdirectory_hints.py` | Replace/augment with ranked symbol context |
| `tools/file_tools.py` | Add `repo_map` tool for on-demand map generation |
| `agent/prompt_builder.py` | Include ranked context in system prompt |
| Skills system | Create a `software-development/repo-map` skill |

### Implementation Difficulty: **Medium**

- tree-sitter Python bindings are mature
- PageRank is ~50 lines of code (networkx or custom)
- Main challenge: caching the graph across turns (invalidate on file changes)
- Hermes already has the `search_files` tool with ripgrep — this complements it

### Concrete Next Steps

```python
# tools/repo_map.py — skeleton
class RepoMapTool:
    def __init__(self, root_dir: str, token_budget: int = 4000):
        self.root = root_dir
        self.budget = token_budget
        self._graph = None  # Lazy-built directed graph
        
    def get_context_for_files(self, active_files: list[str]) -> str:
        """Return ranked context string for the given active files."""
        if not self._graph:
            self._graph = self._build_graph()
        ranked = self._pagerank(seed_files=active_files)
        return self._format_to_budget(ranked)
```


---

## 2. OpenHands — Event-Driven Agent Architecture

**GitHub:** [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | ~50k+ stars | Very Active  
**Language:** Python | **License:** MIT  
**Paper:** ICLR 2025 (arXiv:2407.16741)

### What It Does

OpenHands (formerly OpenDevin) is a platform for AI software development agents. Its core innovation is a clean **event-driven architecture** with sandboxed execution:

- **Stateless Agent** — emits Actions, receives Observations
- **Append-only EventLog** — immutable history of everything that happened
- **Workspace** — Docker container or local process that executes actions
- **Conversation** — orchestrates the loop, manages the event stream

### Key Architecture

```
Agent.step() → Action (tool call) → Workspace.execute() → Observation
     ↑                                                          ↓
     └──────────── EventLog (append-only) ←────────────────────┘
```

**Event Types:**
- `MessageEvent` — user/assistant text
- `ActionEvent` — tool invocations with thought/reasoning/security_risk fields
- `ObservationEvent` — tool results (success or error)
- `CondensationEvent` — context compression markers
- `SystemPromptEvent` — system context with tool schemas

### What to Extract for Hermes

**Component 1: Structured Event Stream**

Hermes currently uses a flat message list. OpenHands' event stream adds:
- Typed events with metadata (timestamps, source attribution, security risk levels)
- Append-only semantics (never mutate history, only append)
- Event-based compression (condense old events without losing the log)

**Component 2: Action/Observation Separation**

Currently Hermes mixes tool calls and results in the message history. Separating them enables:
- Better trajectory analysis (for training data generation)
- Cleaner compression (compress observations, keep actions)
- Security analysis (tag actions with risk levels before execution)

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `agent/trajectory.py` | Already tracks trajectory — enhance with typed events |
| `trajectory_compressor.py` | Use event types for smarter compression decisions |
| `tools/approval.py` | Add `security_risk` field to action events |
| `agent/context_compressor.py` | Condense by event type (keep actions, summarize observations) |
| `run_agent.py` | The main loop already has this shape — formalize it |

### Implementation Difficulty: **Easy-Medium**

Hermes's `run_agent.py` already has an agent loop with tool calls and results. The change is mostly about **formalizing** what's already there:

1. Define an `Event` dataclass hierarchy (Action, Observation, Message, Condensation)
2. Replace raw message dicts with typed events in the trajectory
3. Add metadata fields (timestamp, security_risk, source)
4. Use event types in compression decisions

```python
# agent/events.py — skeleton
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time

class EventType(Enum):
    MESSAGE = "message"
    ACTION = "action"  
    OBSERVATION = "observation"
    CONDENSATION = "condensation"

@dataclass
class Event:
    type: EventType
    timestamp: float = field(default_factory=time.time)
    source: str = ""  # "user", "agent", "tool", "system"
    
@dataclass
class ActionEvent(Event):
    tool_name: str = ""
    arguments: dict = field(default_factory=dict)
    thought: str = ""
    security_risk: str = "low"  # low/medium/high
    
@dataclass
class ObservationEvent(Event):
    tool_name: str = ""
    result: str = ""
    success: bool = True
    truncated: bool = False
```


---

## 3. Goose — Extension System & Custom Distributions

**GitHub:** [aaif-goose/goose](https://github.com/aaif-goose/goose) | ~45.3k stars | Very Active (134 releases)  
**Language:** Rust + TypeScript | **License:** Apache-2.0

### What It Does

Goose (by Block/Square) is an extensible AI developer agent built around MCP. Key innovations:

1. **Extension System** — All tools are MCP servers. Built-in extensions are MCP servers too.
2. **Custom Distributions** — Fork and preconfigure with specific providers, extensions, branding
3. **Session Management** — `goose session --with-extension` dynamically loads tools
4. **Recipes** — Preconfigured workflows with parameters (like Hermes skills but more structured)
5. **Subagents** — Parallel execution with extension scoping per subagent

### Key Architecture

```
Goose Core (Rust)
  ├── Provider Layer (30+ LLM providers, declarative JSON config)
  ├── Extension Manager (MCP client, dynamic loading)
  │     ├── Built-in extensions (developer, computer-controller)
  │     └── User extensions (any MCP server)
  ├── Session Manager (conversation state, working directory)
  ├── Recipe Engine (parameterized workflows)
  └── Subagent Spawner (parallel tasks with scoped extensions)
```

**Extension Loading:**
- `goose session --with-builtin "developer"` — load built-in
- `goose session --with-extension "uvx mcp-server-fetch"` — load any MCP server
- Extensions auto-detected during conversation (Goose asks to enable)

**Recipes (like enhanced Skills):**
```yaml
# recipe.yaml
name: "code-review"
description: "Review code changes"
parameters:
  - name: branch
    type: string
    description: "Branch to review"
steps:
  - prompt: "Review the diff on {{branch}} for security issues"
    extensions: [developer, security-scanner]
```

### What to Extract for Hermes

**Component 1: Dynamic Extension Scoping per Subagent**

Goose's subagent system lets you scope which extensions (tools) each subagent has access to. Hermes's `delegate_task` tool already spawns subagents, but they get the full toolset.

**Implementation:**
```python
# In tools/delegate_tool.py — add toolset scoping
async def delegate_task(task: str, toolset: str = "hermes-cli"):
    """Spawn a subagent with a specific toolset."""
    # Use existing toolsets.py to resolve which tools the subagent gets
    tools = resolve_toolset(toolset)
    # Spawn with restricted tool access
```

**Component 2: Recipe Engine (Structured Workflows)**

Goose recipes are like Hermes skills but with:
- Typed parameters (string, file, choice)
- Multi-step execution with different extension sets per step
- Sub-recipes (composable workflow fragments)

This maps directly to enhancing Hermes's skill system with structured parameters.

**Component 3: Auto-Detection of Needed Extensions**

Goose detects when a task needs an extension that isn't loaded and asks to enable it. Hermes could do this with MCP servers — detect when a task would benefit from a specific MCP server and offer to connect it.

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `tools/delegate_tool.py` | Add `toolset` parameter for scoped subagents |
| `toolsets.py` | Already has the infrastructure — just wire to delegation |
| Skills system | Add parameter schemas to skill YAML frontmatter |
| `hermes_cli/mcp_config.py` | Dynamic MCP server loading mid-session |
| `toolset_distributions.py` | Custom distribution presets |

### Implementation Difficulty: **Easy**

Most of this maps directly to existing Hermes infrastructure:
- Toolset scoping → `toolsets.py` already resolves tool lists
- Recipes → Skills already exist, just add parameter schemas
- Dynamic loading → MCP config already supports hot-reload


---

## 4. Devon — Planning & Task Decomposition

**GitHub:** [entropy-research/Devon](https://github.com/entropy-research/Devon) | ~3k stars | Moderate Activity  
**Language:** Python | **License:** MIT

### What It Does

Devon is an open-source pair programmer focused on multi-step task planning. Its key contribution is a structured planning system that decomposes complex tasks before execution.

**Note:** Devon has pivoted to a "sandbox-agent" model (running coding agents in sandboxes, controlled over HTTP). The original planning architecture is the valuable part.

### Key Architecture

```
User Task → Planner Agent → Task Graph (DAG)
                                ↓
                    Executor (sequential/parallel)
                         ↓           ↓
                    Edit Agent   Test Agent
                         ↓           ↓
                    Linting      Validation
```

**Planning Pattern:**
1. Receive high-level task
2. Decompose into subtasks with dependencies (DAG)
3. Execute subtasks in topological order
4. Each subtask has: description, acceptance criteria, file scope
5. Validate after each subtask (lint, test)
6. Re-plan if validation fails

### What to Extract for Hermes

**Component: Structured Task Planning with Validation Gates**

Hermes has `todo` tool for task tracking, but it's flat (no dependencies, no validation gates). Devon's approach adds:

1. **DAG-based task decomposition** — tasks have dependencies
2. **Validation gates** — run linter/tests after each subtask
3. **Re-planning** — if a subtask fails validation, re-plan remaining tasks
4. **File scoping** — each subtask declares which files it will touch

**Implementation:**
```python
# Enhanced todo_tool.py or new tools/planner.py
@dataclass
class TaskNode:
    id: str
    description: str
    depends_on: list[str] = field(default_factory=list)
    file_scope: list[str] = field(default_factory=list)
    validation: str = ""  # Command to run after completion
    status: str = "pending"  # pending/active/done/failed

class TaskDAG:
    def __init__(self):
        self.nodes: dict[str, TaskNode] = {}
    
    def next_executable(self) -> list[TaskNode]:
        """Return tasks whose dependencies are all 'done'."""
        return [
            n for n in self.nodes.values()
            if n.status == "pending" 
            and all(self.nodes[d].status == "done" for d in n.depends_on)
        ]
```

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `tools/todo_tool.py` | Enhance with dependencies and validation gates |
| `tools/delegate_tool.py` | Execute subtasks as subagent delegations |
| `agent/shell_hooks.py` | Run validation commands after task completion |
| Skills system | `software-development/task-planner` skill |
| Kanban system | Map DAG nodes to kanban tasks for multi-agent execution |

### Implementation Difficulty: **Medium**

- DAG logic is straightforward (~100 lines)
- Validation gates need shell execution + result parsing
- Re-planning requires the agent to reason about failures
- Integration with existing `todo` tool needs careful UX design


---

## 5. Plandex — Version-Controlled Plans

**GitHub:** [plandex-ai/plandex](https://github.com/plandex-ai/plandex) | ~15.4k stars | Active  
**Language:** Go | **License:** AGPL-3.0

### What It Does

Plandex is a terminal-based AI coding agent where **every aspect of a plan is version-controlled**:

1. **Protected Sandbox** — AI changes accumulate in a sandbox, not your actual files
2. **Version History** — Every action creates a new version (context changes, model settings, file edits)
3. **Branches** — Fork a plan to try different approaches
4. **Rewind** — Roll back to any previous state
5. **Diff Review** — Review all pending changes before applying

### Key Architecture

```
Plan (version-controlled unit)
  ├── Context (files added to plan) — versioned
  ├── Conversation (messages) — versioned  
  ├── Pending Changes (sandbox) — versioned
  │     ├── file_a.py: [hunks of changes]
  │     └── file_b.py: [hunks of changes]
  ├── Model Settings — versioned
  └── Applied Changes (committed to disk)
```

**The Sandbox Pattern:**
- AI proposes changes → stored in sandbox (not on disk)
- User reviews diff → `plandex apply` writes to disk
- If something goes wrong → `plandex rewind` rolls back
- Multiple plans can exist simultaneously (different branches of work)

### What to Extract for Hermes

**Component 1: Change Sandbox with Review Gate**

Hermes currently writes files directly via `write_file` and `patch` tools. Plandex's sandbox pattern adds a safety layer:

```python
# tools/sandbox.py — Change accumulator
class ChangeSandbox:
    """Accumulate file changes without writing to disk."""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.pending: dict[str, list[Hunk]] = {}  # path → changes
        self.versions: list[Snapshot] = []
        
    def propose_change(self, path: str, content: str):
        """Stage a change without writing to disk."""
        self.pending.setdefault(path, []).append(Hunk(content))
        self._snapshot()
        
    def apply_all(self) -> list[str]:
        """Write all pending changes to disk. Returns affected paths."""
        for path, hunks in self.pending.items():
            apply_hunks(path, hunks)
        applied = list(self.pending.keys())
        self.pending.clear()
        return applied
        
    def rewind(self, steps: int = 1):
        """Roll back N versions."""
        target = max(0, len(self.versions) - steps)
        self.versions = self.versions[:target]
        self.pending = self.versions[-1].pending if self.versions else {}
```

**Component 2: Plan Branching**

When the agent is unsure about an approach, it could branch:
- Try approach A in one branch
- Try approach B in another
- Compare results, pick the winner

This maps to Hermes's existing checkpoint system (`hermes_cli/checkpoints.py`).

**Component 3: Conversation + Context Versioning**

Every time context changes (file added, message sent, model switched), create a version. This enables:
- "What did the agent know when it made that decision?"
- Replay conversations with different models
- Training data with full provenance

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `tools/file_tools.py` | Add sandbox mode (accumulate, don't write) |
| `tools/checkpoint_manager.py` | Already has checkpoint logic — enhance with plan versioning |
| `hermes_cli/checkpoints.py` | Expose plan branches via CLI |
| `agent/trajectory.py` | Version the trajectory alongside file changes |
| `tools/file_state.py` | Track file state for sandbox diffing |

### Implementation Difficulty: **Medium-Hard**

- Sandbox accumulation is straightforward
- Version history needs storage (SQLite or filesystem)
- Branching requires forking conversation state
- UX challenge: when to auto-apply vs. require review


---

## 6. Letta/MemGPT — Tiered Memory Architecture

**GitHub:** [letta-ai/letta](https://github.com/letta-ai/letta) | ~15k+ stars | Very Active  
**Language:** Python | **License:** Apache-2.0  
**Paper:** arXiv:2310.08560

### What It Does

Letta (formerly MemGPT) implements a **tiered memory system** inspired by OS virtual memory:

1. **Core Memory (Memory Blocks)** — Always in the context window. Structured, editable sections (persona, human, custom blocks). The agent reads/writes these directly.
2. **Archival Memory** — Vector database for long-term storage. Agent searches semantically. Cannot be pinned to context.
3. **Recall Memory** — Conversation history search. Full-text search over past messages.

The key insight: **the agent itself manages its own memory** using tool calls (`core_memory_replace`, `archival_memory_insert`, `archival_memory_search`).

### Key Architecture

```
Context Window (limited)
  ├── System Prompt
  ├── Core Memory Blocks (always present, agent-editable)
  │     ├── persona: "I am Hermes, a self-improving agent..."
  │     ├── human: "User prefers concise responses..."
  │     └── project: "Working on hermes-agent, Python..."
  ├── Recent Messages (sliding window)
  └── Retrieved Context (from archival/recall search)

Archival Memory (unlimited, vector DB)
  └── Semantic search via archival_memory_search tool

Recall Memory (conversation history)
  └── Full-text search via conversation_search tool
```

**Memory Block Pattern:**
```xml
<memory-block label="persona" description="Your identity and capabilities">
I am Hermes, a self-improving AI agent built by Nous Research...
</memory-block>

<memory-block label="human" description="Key details about the user">
Name: Kagan. Prefers direct communication. Working on local AI deployment...
</memory-block>

<memory-block label="project" description="Current project context">
hermes-agent: Python agent with skills, memory, tools, gateway...
</memory-block>
```

### What to Extract for Hermes

**Component 1: Structured Memory Blocks (Core Memory)**

Hermes already has `MEMORY.md` and `USER.md` — but they're flat files. Letta's approach adds:
- **Labeled blocks** with descriptions (agent knows what each block is for)
- **In-context always** (no retrieval needed for core facts)
- **Agent-editable** via specific tools (`core_memory_replace`, `core_memory_append`)
- **Character limits per block** (forces prioritization)

**This is the highest-value integration.** Hermes's memory is already close to this — the enhancement is making blocks structured and always-in-context.

```python
# Enhanced memory_tool.py
MEMORY_BLOCKS = {
    "persona": {
        "description": "Your identity, capabilities, and behavioral guidelines",
        "max_chars": 2000,
        "always_in_context": True,
    },
    "human": {
        "description": "Key details about the user you're conversing with",
        "max_chars": 1500,
        "always_in_context": True,
    },
    "project": {
        "description": "Current project context, tech stack, conventions",
        "max_chars": 2000,
        "always_in_context": True,
    },
    "working_memory": {
        "description": "Temporary scratchpad for current task state",
        "max_chars": 1000,
        "always_in_context": True,
    },
}
```

**Component 2: Archival Memory with Semantic Search**

Hermes has `session_search` (FTS5 over past conversations). Letta adds:
- **Vector-based semantic search** (not just keyword matching)
- **Agent-initiated archival** (agent decides what's worth remembering long-term)
- **Tagged organization** (agent categorizes memories)

**Implementation:** Add a local vector store (ChromaDB or sqlite-vss) alongside the existing FTS5 session search.

**Component 3: Working Memory / Scratchpad**

A dedicated memory block for "what I'm currently doing" that persists across context compressions. This is critical for long-running tasks where compression might lose the current plan.

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `agent/memory_manager.py` | Already has provider pattern — add block-based provider |
| `agent/memory_provider.py` | Implement `LettaStyleProvider` with blocks + archival |
| `tools/memory_tool.py` | Add `core_memory_replace`, `archival_memory_search` tools |
| `agent/prompt_builder.py` | Inject memory blocks into system prompt |
| `kiro-local-config.yaml` | Configure block sizes and archival backend |
| `plugins/memory/` | Implement as a memory plugin |

### Implementation Difficulty: **Medium**

- Memory blocks: Easy (restructure existing MEMORY.md/USER.md)
- Archival with vector search: Medium (need embedding model — can use local sentence-transformers)
- Working memory scratchpad: Easy (just another block)
- The hard part: migration from flat files to structured blocks


---

## 7. CrewAI — Multi-Agent Orchestration

**GitHub:** [crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) | ~51.4k stars | Very Active  
**Language:** Python | **License:** MIT

### What It Does

CrewAI is a role-based multi-agent framework. Key concepts:

1. **Agents** — Each has a role, goal, backstory, and tool access
2. **Tasks** — Specific work items with expected output format
3. **Crews** — Groups of agents that collaborate on tasks
4. **Process** — Sequential or hierarchical (manager delegates to workers)
5. **Flows** — Event-driven orchestration across multiple crews

### Key Architecture

```
Crew
  ├── Process: hierarchical | sequential
  ├── Manager Agent (if hierarchical)
  │     └── Delegates tasks to specialist agents
  ├── Agent: Researcher (tools: web_search, read_file)
  ├── Agent: Developer (tools: terminal, write_file, patch)
  └── Agent: Reviewer (tools: read_file, search_files)

Task
  ├── description: "Implement the authentication module"
  ├── expected_output: "Working auth module with tests"
  ├── agent: Developer
  ├── context: [task_1, task_2]  # Results from previous tasks
  └── output_file: "src/auth.py"
```

**Hierarchical Process:**
```python
crew = Crew(
    agents=[researcher, developer, reviewer],
    tasks=[research_task, implement_task, review_task],
    process=Process.hierarchical,
    manager_llm=ChatOpenAI(model="gpt-4"),
)
```

### What to Extract for Hermes

**Component 1: Role-Based Subagent Profiles**

Hermes's `delegate_task` spawns generic subagents. CrewAI's approach gives each subagent a specialized role:

```python
# Enhanced delegate_tool.py
AGENT_ROLES = {
    "researcher": {
        "system_prompt_addon": "You are a research specialist. Focus on finding information, not implementing.",
        "toolset": "web",  # Only web + file reading tools
        "max_iterations": 20,
    },
    "developer": {
        "system_prompt_addon": "You are a senior developer. Write clean, tested code.",
        "toolset": "hermes-cli",  # Full tool access
        "max_iterations": 40,
    },
    "reviewer": {
        "system_prompt_addon": "You are a code reviewer. Find bugs, suggest improvements. Do NOT modify files.",
        "toolset": "safe",  # Read-only tools
        "max_iterations": 15,
    },
}
```

**Component 2: Task Context Chaining**

CrewAI passes results from earlier tasks as context to later tasks. Hermes's kanban system already has this concept (task dependencies), but it could be formalized:

```python
# Task result flows to dependent tasks
task_2.context = [task_1.output]  # task_2 sees task_1's result
```

**Component 3: Hierarchical Delegation**

A "manager" agent that doesn't do work itself but delegates to specialists:
- Analyzes the task
- Breaks it into subtasks
- Assigns to the right specialist agent
- Reviews results and re-delegates if needed

This maps to Hermes's kanban orchestrator pattern.

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `tools/delegate_tool.py` | Add `role` parameter with predefined profiles |
| `toolsets.py` | Role → toolset mapping (already exists!) |
| `tools/kanban_tools.py` | Hierarchical delegation via kanban |
| `agent/prompt_builder.py` | Inject role-specific system prompt addons |
| Skills system | `autonomous-ai-agents/crew-orchestrator` skill |

### Implementation Difficulty: **Easy**

Hermes already has all the building blocks:
- `delegate_task` tool for spawning subagents
- `toolsets.py` for scoping tool access
- Kanban system for multi-agent coordination
- The missing piece is just **role profiles** — a dict mapping role names to configs


---

## 8. SWE-agent — Agent-Computer Interfaces

**GitHub:** [SWE-agent/SWE-agent](https://github.com/SWE-agent/SWE-agent) | ~20k+ stars | Active  
**Language:** Python | **License:** MIT  
**Paper:** NeurIPS 2024 (arXiv:2405.15793)

### What It Does

SWE-agent's core thesis: **LLMs are a new kind of end user that need interfaces designed for them, not for humans.** Key innovations:

1. **Windowed File Viewer** — Shows files in a scrollable window (100 lines at a time) with line numbers
2. **Lint-on-Edit Guard** — Automatically lints after every edit, rejects if syntax errors introduced
3. **Search with Truncation** — Search results are truncated to prevent context overflow
4. **Tool Bundles** — YAML-defined tool sets uploaded as bash/Python scripts into the sandbox
5. **State Command** — After every action, a state command runs and returns structured JSON (cwd, open file, etc.)

### Key Architecture

```
Agent Loop
  ├── LLM generates action (tool call)
  ├── Execute in sandbox (SWE-ReX runtime)
  ├── Run state command → get structured state JSON
  ├── If edit: run linter → reject if errors
  ├── Truncate output if too long
  └── Return observation to LLM

Tool Bundles (YAML config):
  tools:
    open:
      signature: "open <path> [<line_number>]"
      docstring: "Opens file at given path in the file viewer"
    scroll_down:
      signature: "scroll_down"
      docstring: "Moves the window down 100 lines"
    edit:
      signature: "edit <start_line>:<end_line>\n<replacement_text>\nend_of_edit"
      docstring: "Replaces lines start_line through end_line"
```

**mini-swe-agent (v2):** The team's latest insight — you don't need complex tool interfaces. A minimal 100-line agent with just bash access scores 74% on SWE-bench. The key is the **model**, not the scaffolding.

### What to Extract for Hermes

**Component 1: Lint-on-Edit Guard**

Automatically validate edits before accepting them. If the edit introduces syntax errors, reject it and tell the agent to fix it.

```python
# tools/file_tools.py — add to write_file/patch
def _lint_after_edit(filepath: str) -> Optional[str]:
    """Run linter on file after edit. Return error string or None."""
    ext = Path(filepath).suffix
    linters = {
        ".py": ["python", "-m", "py_compile", filepath],
        ".js": ["npx", "eslint", "--no-eslintrc", filepath],
        ".ts": ["npx", "tsc", "--noEmit", filepath],
    }
    cmd = linters.get(ext)
    if not cmd:
        return None
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if result.returncode != 0:
        return f"Edit introduced errors:\n{result.stderr[:500]}"
    return None
```

**Component 2: Structured State After Every Action**

After every tool call, return a structured state summary. This helps the agent maintain awareness of its environment:

```json
{
  "cwd": "/home/user/project",
  "open_file": "src/auth.py",
  "open_file_lines": "45-145 of 300",
  "git_status": "modified: src/auth.py, src/tests/test_auth.py",
  "last_test_result": "PASS"
}
```

**Component 3: Output Truncation with Indicators**

SWE-agent truncates long outputs and tells the agent it was truncated. Hermes already has `tools/tool_output_limits.py` — but SWE-agent's approach is more informative:

```
[Output truncated: showing first 200 of 1,847 lines. Use search_files to find specific content.]
```

**Component 4: YAML Tool Bundles (for custom tool definitions)**

Define tools as YAML with signature + docstring. This is simpler than Python tool definitions for quick prototyping:

```yaml
# tools/bundles/git-tools.yaml
tools:
  git_diff:
    signature: "git_diff [--staged] [path]"
    docstring: "Show changes in working directory or staging area"
    implementation: "git diff $@"
  git_log:
    signature: "git_log [--oneline] [-n N]"
    docstring: "Show recent commit history"
    implementation: "git log $@"
```

### Integration with Hermes Architecture

| Hermes Component | Integration Point |
|---|---|
| `tools/file_tools.py` | Add lint-on-edit guard to `write_file` and `patch` |
| `tools/tool_output_limits.py` | Enhance truncation with informative messages |
| `tools/terminal_tool.py` | Add structured state output after commands |
| `agent/shell_hooks.py` | Post-edit validation hooks |
| `tools/registry.py` | YAML-based tool bundle loading |
| `model_tools.py` | Inject state summary into tool results |

### Implementation Difficulty: **Easy**

- Lint-on-edit: ~30 lines, immediate value
- Output truncation enhancement: ~10 lines
- State command: Medium (need to decide what state to track)
- YAML tool bundles: Medium (need a loader, but tools/registry.py is extensible)


---

## 9. Priority Integration Roadmap

### Tier 1: Quick Wins (1-2 days each, immediate value)

| # | Feature | Source | Effort | Impact |
|---|---------|--------|--------|--------|
| 1 | **Lint-on-Edit Guard** | SWE-agent | Easy | Prevents broken code from accumulating |
| 2 | **Role-Based Subagent Profiles** | CrewAI | Easy | Better delegation with `delegate_task` |
| 3 | **Toolset-Scoped Delegation** | Goose | Easy | Restrict subagent tool access |
| 4 | **Enhanced Output Truncation** | SWE-agent | Easy | Better agent awareness of truncated output |

### Tier 2: High-Value Medium Effort (3-5 days each)

| # | Feature | Source | Effort | Impact |
|---|---------|--------|--------|--------|
| 5 | **Structured Memory Blocks** | Letta/MemGPT | Medium | Always-in-context structured memory |
| 6 | **Typed Event Stream** | OpenHands | Medium | Better trajectory data, smarter compression |
| 7 | **DAG-Based Task Planning** | Devon | Medium | Multi-step tasks with validation gates |
| 8 | **Working Memory Scratchpad** | Letta/MemGPT | Easy-Med | Survives compression, tracks current state |

### Tier 3: Strategic Investments (1-2 weeks each)

| # | Feature | Source | Effort | Impact |
|---|---------|--------|--------|--------|
| 9 | **PageRank Repo Map** | Aider | Medium | Automatic context selection for coding tasks |
| 10 | **Change Sandbox** | Plandex | Med-Hard | Review AI changes before applying |
| 11 | **Archival Memory (Vector)** | Letta/MemGPT | Medium | Semantic search over long-term knowledge |
| 12 | **YAML Tool Bundles** | SWE-agent | Medium | Quick tool prototyping without Python |

### Tier 4: Architectural Enhancements (2+ weeks)

| # | Feature | Source | Effort | Impact |
|---|---------|--------|--------|--------|
| 13 | **Plan Branching** | Plandex | Hard | Try multiple approaches, pick winner |
| 14 | **Hierarchical Multi-Agent** | CrewAI | Med-Hard | Manager agent delegates to specialists |
| 15 | **Dynamic Extension Loading** | Goose | Medium | Load MCP servers on-demand mid-session |

---

## Implementation Notes for kiro-cli Local Deployment

### Context Budget Considerations

With kiro-cli providing 1M token context (Claude Opus 4.6), several patterns become more practical:

- **Repo Map:** Can include much more context (budget 50k tokens for repo map vs. Aider's typical 4k)
- **Memory Blocks:** Can afford larger blocks (5k chars each vs. Letta's typical 2k)
- **Event Stream:** Full event history fits longer before compression needed
- **Change Sandbox:** Can show full diffs in context without truncation

### Local-Only Advantages

- **No rate limits** → Lint-on-edit can re-run freely
- **No API costs** → Subagent delegation is "free" (just time)
- **Full disk access** → Sandbox can use git worktrees for branching
- **Persistent state** → Memory blocks persist in `~/.hermes/` filesystem

### Recommended First Implementation

Start with items 1-4 (Tier 1) as they require minimal code changes:

```bash
# 1. Lint-on-Edit: Add to tools/file_tools.py
# 2. Role Profiles: Add AGENT_ROLES dict to tools/delegate_tool.py  
# 3. Scoped Delegation: Add toolset param to delegate_task schema
# 4. Better Truncation: Enhance tools/tool_output_limits.py
```

Then move to item 5 (Structured Memory Blocks) as it has the highest long-term impact for a persistent local agent.

---

## Cross-Cutting Patterns

### Pattern: "Agent Manages Its Own State"

Seen in: Letta (memory), Plandex (plans), OpenHands (events)

The agent should be able to:
- Read its own state (memory blocks, task list, file state)
- Write its own state (update memory, mark tasks done, stage changes)
- Search its own history (archival memory, session search, event log)

Hermes already does this with memory + todo + session_search. The enhancement is making it more structured and always-in-context.

### Pattern: "Validation After Every Mutation"

Seen in: SWE-agent (lint-on-edit), Devon (test after subtask), Plandex (diff review)

Every time the agent changes something, validate immediately:
- File edit → lint
- Code change → run relevant tests
- Config change → validate syntax
- Task completion → run acceptance criteria

### Pattern: "Scoped Tool Access"

Seen in: Goose (extension scoping), CrewAI (role-based tools), SWE-agent (tool bundles)

Not every agent/subagent needs every tool. Scope tools to:
- The current task (coding task → developer tools only)
- The agent's role (reviewer → read-only tools)
- Security level (untrusted task → sandboxed tools only)

Hermes's `toolsets.py` already supports this — it just needs to be wired to delegation.

### Pattern: "Automatic Context Selection"

Seen in: Aider (repo map), OpenHands (condenser), Letta (memory retrieval)

Don't make the agent manually find context. Automatically provide:
- Relevant code symbols (repo map)
- Relevant memories (semantic search)
- Relevant past conversations (recall)
- Current project state (working memory block)

---

## References

- Aider Repo Map: https://aider.chat/2023/10/22/repomap.html
- OpenHands SDK Architecture: https://docs.openhands.dev/sdk/arch/agent
- Goose Custom Distributions: https://github.com/aaif-goose/goose/blob/main/CUSTOM_DISTROS.md
- Plandex Version Control: https://docs.plandex.ai/core-concepts/version-control/
- Letta Memory Blocks: https://docs.letta.com/guides/core-concepts/memory/memory-blocks/
- Letta Archival Memory: https://docs.letta.com/guides/core-concepts/memory/archival-memory/
- CrewAI Framework: https://github.com/crewAIInc/crewAI
- SWE-agent Architecture: https://swe-agent.com/0.7/background/architecture/
- SWE-agent Tool Bundles: https://swe-agent.com/latest/config/tools/
- mini-swe-agent: https://github.com/SWE-agent/mini-swe-agent
- Hermes Issue #535 (PageRank Repo Map): https://github.com/NousResearch/hermes-agent/issues/535
