# Interesting Issues & Ideas from NousResearch/hermes-agent

> Research date: 2026-05-16
> Focus: Ideas valuable for LOCAL-ONLY deployment using kiro-cli as the LLM backbone

---

## Table of Contents

1. [Context & Memory Architecture](#1-context--memory-architecture)
2. [Local-Only Usage & Custom Providers](#2-local-only-usage--custom-providers)
3. [Agent Self-Improvement & Learning](#3-agent-self-improvement--learning)
4. [Performance Optimizations (Local Models)](#4-performance-optimizations-local-models)
5. [Security & Sandboxing](#5-security--sandboxing)
6. [Streaming & Real-Time Features](#6-streaming--real-time-features)
7. [Plugin & Extension Architecture](#7-plugin--extension-architecture)
8. [OpenAI-Compatible API Server](#8-openai-compatible-api-server)

---

## 1. Context & Memory Architecture

### #499 — Context Compaction Quality Overhaul (CLOSED, 7 comments)

**Key Ideas:**
- Structured handoff-oriented compression prompts (9-section format from Roo Code)
- Direct quotes from user messages to prevent "telephone game" drift
- Multi-unit summarization triggers (fraction, tokens, messages) from DeerFlow
- Iterative re-compression that updates existing summary instead of re-summarizing
- No encryption of compacted context (plaintext, debuggable, transparent)

**Community Consensus:** Largely implemented in #10088. Remaining gaps:
- @context file contents permanently lost after compaction (P0 fix: ~20 lines)
- Tool call details truncated BEFORE summarizer sees them (500/3000 char caps)
- No degradation warning on repeated compressions
- Summary quality bottlenecked by auxiliary model

**Implementation Feasibility for Local:** HIGH — All of this applies directly. With kiro-cli as backbone, the compression model IS the main model (no separate "cheap" auxiliary). The structured handoff prompt and file re-injection are trivial to implement.

---

### #8457 — Persistent Session Memory with Cross-Session Search (8 comments)

**Key Ideas:**
- Per-thread markdown session files that auto-load on wake
- Auto-save checkpoints at state changes (bug fixed, decision made)
- Cross-session search via SQLite FTS5 or simple ripgrep
- Auto-compression lifecycle: Active → Recent → Archive → Ancient
- Master archive index for all sessions

**Community Consensus:** Active development. PR #7185 covers Neural Memory provider. Community wants simple, file-based persistence that survives restarts.

**Implementation Feasibility for Local:** HIGH — Perfect for local-only. No cloud dependency. SQLite + markdown files on disk. The session vault pattern maps directly to a local filesystem approach.

---

### #12883 — Memory Importance Scoring (1 comment)

**Key Ideas:**
- No mechanism to determine what's worth preserving vs. temporary
- "Save everything" leads to bloated, noisy memory
- Need decay/importance recalculation (write-only memory is broken)
- Four fragmented memory surfaces (memory.md, user profile, sessions, skills) with no unified retrieval
- Session breaks = unpredictable context loss

**Community Consensus:** Users agree — agent adds useless entries automatically. Need signal vs. noise discrimination.

**Implementation Feasibility for Local:** MEDIUM — Requires an importance-scoring pass (could be a local LLM call or heuristic). The unified memory surface is an architectural decision. For local deployment, a simple relevance decay + frequency-based scoring would work without extra LLM calls.

---

### #553 — Subconscious Observer Agent (Background Memory Processing)

**Key Ideas:**
- Separate "subconscious" agent observes session transcripts asynchronously
- Extracts patterns and injects guidance without conscious agent thinking about memory
- 8 structured memory blocks (core_directives, guidance, user_preferences, project_context, session_patterns, pending_items, self_improvement, tool_guidelines)
- "Sleep-time compute" — process information during downtime
- Blocks at decision points for 2-5 seconds to inject advisory guidance

**Community Consensus:** Architecturally compelling but no implementation yet. Hermes has the infrastructure (auxiliary_client, flush_memories, session_search).

**Implementation Feasibility for Local:** MEDIUM-HIGH — With kiro-cli running locally, a background process can run the "subconscious" during idle time. The 8-block memory structure is elegant and implementable as local files. Main challenge: coordinating the observer with the main agent loop.

---

### #5563 — Field Report: Memory Persistence & Token Waste (3 comments)

**Key Ideas:**
- Session fragmentation causes exponential token replay (89% waste observed)
- state.db SQLite corruption from concurrent access (WAL mode + multiple processes)
- Agent hallucinated being in a cloud container after hours of local work
- 2.6M tokens lost in a single day to context replay overhead

**Community Consensus:** Critical production issue. Multiple users confirm state.db corruption. JSON session files survive but DB doesn't.

**Implementation Feasibility for Local:** HIGH — Essential to solve for any local deployment. Use proper SQLite locking, incremental context (compressed summary instead of full replay), and visible session boundary indicators.

---

## 2. Local-Only Usage & Custom Providers

### #19091 — Improved Local Ollama Discovery & First-Class Custom Providers

**Key Ideas:**
- Setup wizard creates a loop where users can't select local-only workflow
- Need explicit "Local Ollama (Custom Host)" option without cloud API key
- Flag to completely disable cloud-based discovery (100% privacy)
- Better handling of `--provider custom` so it doesn't default back to OpenRouter
- Distributed setup support (MacBook client + Windows GPU via Tailscale)

**Community Consensus:** Users want a clean local-only path without dummy API keys or env var hacking.

**Implementation Feasibility for Local:** CRITICAL — This is exactly our use case. The kiro-cli wrapper needs to present as a clean local provider that Hermes discovers without cloud fallback attempts.

---

### #21992 — First-Class Local Brain Layer (2 comments)

**Key Ideas:**
- Local model handles persistent low/medium complexity cognition
- Cloud model remains strongest reasoning layer (or in our case, kiro-cli IS the brain)
- Agent-level cognitive roles: preprocess, compress, classify, draft, watch
- Visible routing and audit (show when local vs cloud was used)
- Safety boundaries: local brain proposes/filters/summarizes, doesn't execute directly

**Architecture:**
```
Hermes Agent = local brain + cloud brain + tools + memory + policy/router
```

**Community Consensus:** Strong interest. Distinction from "just support Ollama" — this is about cognitive architecture, not just provider support.

**Implementation Feasibility for Local:** HIGH — With kiro-cli as the sole brain, this simplifies to a single-brain architecture. The cognitive roles (preprocess, compress, classify) can be implemented as different prompt templates sent to the same local model.

---

### #3577 — Hardcoded Context Window Limits (CLOSED, 7 comments)

**Key Ideas:**
- Context window hardcoded per model, doesn't respect actual limits
- Local Ollama models report wrong context size (128K reported as 256K)
- Fix: `model.context_length` config override in config.yaml
- Auto-detection via 429 error + automatic reduction + retry

**Community Consensus:** Fixed via config override. Important for local models where context varies by quantization and hardware.

**Implementation Feasibility for Local:** HIGH — Must configure correctly for kiro-cli's actual context window. The config override pattern is already implemented.

---

### #3926 — Add Ollama Cloud as Built-in Provider (7 comments)

**Key Ideas:**
- Dynamic model discovery (live API + models.dev, disk-cached)
- Local Ollama experience needs improvement (can't add as fallback provider)
- Better local provider support "coming soon" per maintainers

**Community Consensus:** Users eager for first-class local model support. Current experience is friction-heavy.

**Implementation Feasibility for Local:** HIGH — The dynamic model discovery pattern is useful. For kiro-cli, we'd implement a similar discovery mechanism that queries the local endpoint for available models.

---

## 3. Agent Self-Improvement & Learning

### #337 — Evolutionary Self-Improvement (3 comments, hermes-forge repo created)

**Key Ideas:**
- LLM-driven evolutionary optimization (2-3x performance improvements)
- Population management, fitness-weighted selection, LLM-driven mutation
- Failure-driven mutation (targeted at specific failure cases, not random)
- Learning logs prevent re-trying failed approaches
- Post-mutation verification (>10x cost reduction)
- DSPy + GEPA integration for skill/prompt optimization

**Community Consensus:** Active development. `hermes-forge` repo created with Phase 1 (skill evolution via DSPy + GEPA) implemented.

**Implementation Feasibility for Local:** MEDIUM — Requires significant compute for evolutionary search. With a local model, iterations are "free" (no API cost) but slow. Best suited for overnight batch optimization of skills and prompts. The GEPA approach (reads execution traces to understand WHY failures happen) is particularly valuable locally since all traces are on disk.

---

### #483 — Post-Task Reflection & Missing Affordance Detection (2 comments)

**Key Ideas:**
- Structured post-task reflection with failure classification:
  - incorrect_task_interpretation
  - incorrect_world_assumption
  - **missing_affordance** (key one)
  - tool_limitation_or_misbehavior
  - exhausted_or_misdirected_search
- Automatic gap detection → logged opportunity → skill/tool creation
- Codex's two-phase async memory pipeline: extract on next startup (min 6 hours idle)
- Enso's session-end distillation / error-to-lesson loop

**Community Consensus:** Strong architectural alignment with Hermes's existing infrastructure. The "failure → reflection → gap detection → skill creation" loop is the holy grail.

**Implementation Feasibility for Local:** HIGH — Perfect for local. All session data is on disk. A post-session reflection pass (run during idle time) can classify failures and accumulate lessons. No cloud dependency. The "missing affordance" detection is particularly valuable for identifying what tools/skills to build next.

---

### #21303 — Persistent Specialized Subagents with Private Skill Lifecycle (5 comments)

**Key Ideas:**
- Self-improvement belongs to specialized subagents, not the main agent
- Main agent's task distribution is too broad — experience drifts laterally
- Subagents anchored to stable professional identity continuously distill execution experience
- Skill refinement loop: lesson-inbox → review-gate → promoted-rule
- Cold-start problem: new subagents need an opening hypothesis (role playbook)

**Community Consensus:** Architecturally compelling. Debate between "where skill evolution lives" (main agent vs. persistent role-scoped subagents). External repos exploring the pattern.

**Implementation Feasibility for Local:** MEDIUM — Requires persistent subagent state across sessions. With local storage, this is feasible but adds complexity. The key insight (narrow, repeated learning signals converge better than broad ones) is valuable for designing specialized local agents.

---

### #498 — Conversational RL Personalization (CLOSED by maintainer)

**Key Ideas:**
- "Next-state as reward signal" — user's follow-up message evaluates previous response
- Process Reward Model judges (response, next_state) pairs
- No manual labeling needed — natural conversation flow provides signal

**Community Consensus:** Maintainer closed with "not pursuing this direction." Too heavy for the project's scope.

**Implementation Feasibility for Local:** LOW — Requires training infrastructure (SGLang, Megatron-LM). Not practical for local-only deployment. However, the "next-state as reward signal" concept could inform simpler preference learning.

---

## 4. Performance Optimizations (Local Models)

### #4319 — KV Cache Invalidation on Compression (5 comments)

**Key Ideas:**
- Every context compression cycle invalidates KV cache by rebuilding system prompt
- Forces model to reprocess full context from scratch (multi-minute pauses on 35B MoE)
- Fix 1: Skip rebuild when memory content hasn't changed
- Fix 2: Prefix-stable prompt ordering (volatile sections at END)
- Fix 3: Config option to disable memory-in-system-prompt for local models

**Proposed prompt structure for cache stability:**
```
[STABLE] Agent identity (SOUL.md)
[STABLE] Skills guidance
[STABLE] Context files (AGENTS.md)
[STABLE] Tool definitions
[VOLATILE] Memory snapshot
[VOLATILE] Compression summary note
[VOLATILE] Date/time
```

**Community Consensus:** Users confirm multi-minute pauses. Partial fix in #8689 (timestamp no longer changes). Memory content changes still invalidate.

**Implementation Feasibility for Local:** CRITICAL — This is the #1 performance issue for local models. With kiro-cli, KV cache preservation is essential. The prefix-stable ordering is a simple architectural change with massive impact.

---

### #525 — /microcompact: LLM-Free Surgical Context Stripping

**Key Ideas:**
- Strip tool call/result pairs and thinking blocks WITHOUT LLM summarization
- Instant, free, lossless for actual conversational content
- Context is often 70-90% tool call/result pairs and thinking blocks
- Three-layer system: microcompact (silent, every turn) → auto-compact (threshold) → /compact (manual)
- Keep a "hot tail" of N most recent tool results intact

**Community Consensus:** "compact is a grenade. This is a scalpel." Strong support for surgical, LLM-free context management.

**Implementation Feasibility for Local:** HIGH — Zero cost, instant execution. Perfect for local models with limited context windows. Implement as a pre-processing step before each API call.

---

### #535 — PageRank Repo Map (Automatic Codebase Context Selection) (2 comments)

**Key Ideas:**
- Build directed graph of symbol definitions/references across codebase
- Personalized PageRank ranks files by relevance to current conversation
- Scope-aware elided code views that fit within token budget
- Tree-sitter for symbol extraction, SQLite cache with mtime invalidation
- Automatic, graph-based, zero-effort context that adapts to conversation

**Community Consensus:** Skill-based first step implemented (#4413). Full automatic injection deferred due to prompt caching concerns.

**Implementation Feasibility for Local:** MEDIUM — Tree-sitter parsing is fast and local. The graph computation is CPU-only. Main challenge: fitting the repo map within limited local model context windows. The token budget approach is essential.

---

### #26806 — Suppress Skills Index Injection for Scripted Use

**Key Ideas:**
- `<available_skills>` block is ~14k chars / ~3.5k input tokens per call
- For scripted/oneshot use, this is pure overhead (~42M input tokens/day for one deployment)
- Need `--no-skills-index` flag or `skills.inject_index: false` config

**Community Consensus:** Clear need for high-frequency callers. Related to lazy skill loading (#12379, #13980).

**Implementation Feasibility for Local:** HIGH — Essential for local models with limited context. Every token saved matters. Simple config flag to suppress.

---

## 5. Security & Sandboxing

### #7826 — Security Audit: 4 Critical, 9 High Severity Findings

**Critical Findings:**
1. Unrestricted shell command execution (local backend) — `bash -c` via subprocess
2. Full filesystem read access with no deny list — can read SSH keys, .env files
3. Approval bypass for containerized environments — ALL checks skipped
4. LLM can create persistent skills without sandbox — prompt injection vectors

**Good News:**
- No malware, backdoors, or data exfiltration
- No telemetry or phone-home behavior
- API keys sent only to intended providers
- Comprehensive log redaction (30+ patterns)
- SSRF protection, file permissions, credential stripping

**Implementation Feasibility for Local:** CRITICAL — For local-only deployment, C1 (unrestricted shell) and C2 (full filesystem read) are acceptable IF the user trusts the model. But for a shared/multi-user local deployment, these need addressing. Consider: configurable deny lists, approval gates for dangerous operations, and skill creation sandboxing.

---

### #527 — Gateway Permission Tiers (RBAC) (6 comments)

**Key Ideas:**
- Owner → Admin → User → Guest permission tiers
- Per-message enforcement (not per-chat)
- Tool-level gating (terminal, write_file, schedule_cronjob restricted by tier)
- Per-command gating (/model, /update, /reload-mcp restricted)
- Session sharing policy: full tool set loaded, permissions enforced per-message

**Community Consensus:** Maintainer provided opinionated answers. Per-message enforcement chosen over "most restrictive in chat."

**Implementation Feasibility for Local:** MEDIUM — Relevant if exposing the agent to multiple users (e.g., family members, team). For single-user local deployment, less critical. The tool-level gating pattern is useful for self-imposed safety boundaries.

---

### #7071 — Code Execution Sandbox Exposes Internal Modules (3 comments)

**Key Ideas:**
- PYTHONPATH injection leaks configuration secrets and security rules
- Skills guard bypass via dynamic import and string construction
- Silent environment variable exfiltration possible

**Implementation Feasibility for Local:** MEDIUM — For local-only with trusted models, lower risk. But if running untrusted skills or community plugins, sandboxing becomes important.

---

## 6. Streaming & Real-Time Features

### Streaming Support (from .plans/streaming-support.md)

**Key Ideas:**
- Feature-flagged, callback-based, graceful degradation
- `stream_callback(text_delta: str)` injected into AIAgent
- Queue-based bridge between agent thread and consumer
- Platform-specific edit intervals (Telegram 1.5s, Discord 1.2s)
- Phase 1: Core infrastructure → Phase 2: Gateway → Phase 3: CLI → Phase 4: API Server

**Implementation Feasibility for Local:** HIGH — Essential for UX with local models (which generate slower). The callback-based architecture is clean and works regardless of backend. With kiro-cli, streaming would show tokens as they're generated locally.

---

### #11712 — Local WebSocket Interface for Third-Party Clients (2 comments)

**Key Ideas:**
- Minimal local WebSocket server for real-time bidirectional messaging
- Methods: agents.list, message.send, session.list, session.get
- Events: agent.thinking, agent.tool_call, agent.done
- Authentication via local token
- PR #20564 implements a generic WebSocket bridge

**Implementation Feasibility for Local:** HIGH — Perfect for local deployment. Enables mobile apps, custom UIs, and multi-client access to the local agent. The WebSocket protocol is lightweight and well-suited for local networking.

---

## 7. Plugin & Extension Architecture

### #359 — Enhanced Extension System with Tool Interception (6 comments)

**Key Ideas:**
- 30+ lifecycle events with ability to block tool calls, modify results, transform context
- Tool interception: block dangerous commands, modify arguments before execution
- Context modification before LLM sees it
- Event cancellation for safety gates
- Pi coding agent as reference implementation

**Community Consensus:** Strong interest. Users want: block dangerous tool calls, modify tool arguments, force agent to keep working, inject context, auto-approve safe operations, use LLM to evaluate actions.

**Implementation Feasibility for Local:** HIGH — The hook/interception pattern is essential for local deployment safety. Implement as a middleware layer between the agent loop and tool execution. Enables custom approval gates, audit logging, and context injection without modifying core code.

---

### #18148 — Runtime Extension Hooks (transform_user_input, before_llm_call, intercept_tool_call)

**Key Ideas:**
- `transform_user_input` — modify user message before agent sees it
- `before_llm_call` — modify messages/system prompt before LLM call
- `intercept_tool_call` — approve/deny/modify tool calls

**Implementation Feasibility for Local:** HIGH — Three hooks that cover 90% of extension needs. Simple to implement as a plugin interface.

---

## 8. OpenAI-Compatible API Server

### From .plans/openai-api-server.md + #8881

**Key Ideas:**
- Expose `POST /v1/chat/completions` (streaming + non-streaming)
- Expose `GET /v1/models` and `GET /health`
- Gateway Platform Adapter pattern (reuses all gateway infrastructure)
- Hybrid session management: stateless by default, opt-in persistent via X-Session-ID
- Compatible with Open WebUI, LobeChat, LibreChat, AnythingLLM, NextChat, etc.
- Bearer token auth, localhost-only by default

**Community Consensus:** Already partially implemented (docs exist). Users confirm it works. Essential for ecosystem integration.

**Implementation Feasibility for Local:** CRITICAL — This is how kiro-cli would present itself to Hermes. The OpenAI-compatible API is the universal interface. Our kiro-openai-wrapper already implements this pattern. The key insight: Hermes can both CONSUME and EXPOSE this API.

---

## Summary: Top 10 Ideas for Local-Only kiro-cli Deployment

| Priority | Issue | Idea | Effort |
|----------|-------|------|--------|
| **P0** | #4319 | KV cache-stable prompt ordering | Small |
| **P0** | #19091 | Clean local-only provider path (no cloud fallback) | Medium |
| **P0** | #525 | /microcompact: LLM-free surgical context stripping | Small |
| **P1** | #499 | Structured handoff compression + @context re-injection | Medium |
| **P1** | #8457 | Persistent session memory with cross-session search | Medium |
| **P1** | Streaming | Token-by-token streaming for local model UX | Medium |
| **P2** | #483 | Post-task reflection & missing affordance detection | Medium |
| **P2** | #337 | Evolutionary self-improvement (overnight batch) | Large |
| **P2** | #553 | Subconscious observer (background memory processing) | Large |
| **P3** | #359 | Tool interception hooks for safety & extensibility | Medium |

---

## Architecture Implications for kiro-cli Integration

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                     │
│         (CLI / TUI / WebSocket / API Server)         │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│              Hermes Agent Core Loop                   │
│  ┌─────────────┐  ┌──────────┐  ┌───────────────┐  │
│  │ Tool Hooks  │  │ Context  │  │ Memory/Skills │  │
│  │ (intercept) │  │ Manager  │  │ (local files) │  │
│  └─────────────┘  └──────────┘  └───────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────┐
│           kiro-cli OpenAI-Compatible API              │
│  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │
│  │ Streaming│  │ KV Cache  │  │ Context Window  │  │
│  │ Support  │  │ Preserved │  │ Management      │  │
│  └──────────┘  └───────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────┘
```

**Key Design Principles for Local-Only:**
1. Every token counts — aggressive context management (microcompact + structured compression)
2. KV cache is sacred — never invalidate unnecessarily
3. All data stays local — memory, sessions, skills on filesystem
4. Background processing is free — use idle time for reflection, memory consolidation
5. Single model, multiple roles — same kiro-cli handles main reasoning + compression + classification via different prompt templates
