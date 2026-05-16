# Interesting Unmerged PRs — NousResearch/hermes-agent

> Generated 2025-05-16. Focus: architectural improvements, local/CLI usage, memory,
> agent loop, provider system, streaming, context compression, and skill system.

---

## 🧠 Agent Loop & Performance Optimizations

### PR #26905 — `perf(run_agent): cache-stable mode — trim verification + reduce tool-result budgets for recurring single-wake spawns`
**Labels:** type/perf, comp/agent  
**Impact:** HIGH — directly reduces token usage and turn count for cron/queue workloads

**Key Ideas:**
- Opt-in "cache-stable mode" for recurring single-wake spawns (cron, queue workers)
- **Verification trim**: Replaces the aggressive per-step "verify/re-read after every mutation" with a single end-of-run confirmation
- **Reduced tool-result budgets**: Lowers per-result/per-turn char budgets (20k/60k) so high-turn flows don't accumulate giant uncached context
- Measured 30-40 model turns where equivalent agents ran 10-15 on identical work — driven by verification block forcing re-reads
- Default OFF — interactive behavior byte-identical when unset
- Activation: `HERMES_CACHE_STABLE` env var or `agent.cache_stable: true` config key

**Implementation Notes:**
- `run_agent.py`: `self._cache_stable_mode` flag + `self._cache_stable_budget` (reduced `BudgetConfig`)
- `agent/prompt_builder.py`: `OPENAI_MODEL_EXECUTION_GUIDANCE_CACHE_STABLE` variant with import-time assert to prevent drift
- Preserves `PINNED_THRESHOLDS` (read_file=inf) and 3-layer persistence (full payloads still in sandbox)
- Companion to prefix-stability work (PR #23438)

---

### PR #26908 — `feat(agent): inject iteration budget pressure hints`
**Labels:** type/feature, comp/agent  
**Impact:** MEDIUM — helps model self-regulate before hitting hard max-iteration limit

**Key Ideas:**
- Lightweight iteration-budget pressure hints at 70% and 90% of `max_iterations`
- Gives the model advance signal to consolidate findings or produce a final answer
- Currently Hermes only asks the model to summarize AFTER exhausting the loop budget
- Hint is appended to per-call `api_messages` copy only — does NOT mutate persisted history or stable system prompt cache prefix

**Implementation Notes:**
- Two fixed pressure tiers in `run_agent.py`
- System-reminder style user message (ephemeral copy)
- Refs issue #414; intentionally small first slice — configurable thresholds in later phases

---

### PR #27045 — `fix(agent): improve empty-response recovery with truncation fallback`
**Labels:** type/bug, comp/agent, P2  
**Impact:** MEDIUM — fixes context overflow when LLM summarization fails

**Key Ideas:**
- When LLM summarization-based context compression fails, replaces static placeholder with truncation fallback
- Truncation strategy: keep head messages + last N messages, discard the middle
- Injects brief truncation notice into system message
- Adds "NEVER return empty content" directive to agent identity prompt
- Reduces empty-response retry limit from 3 to 2 (faster fail-forward)

**Implementation Notes:**
- `agent/context_compressor.py`: head+tail truncation with `_sanitize_tool_pairs`
- `agent/prompt_builder.py`: explicit instruction to process tool results
- `run_agent.py`: simplified recovery prompt, reduced retries

---

## 🔌 Provider System & Local Backend Support

### PR #27042 — `fix(model-switch): probe /models for custom providers without api_key`
**Labels:** type/bug, comp/cli, comp/gateway, P2  
**Impact:** HIGH for local users — enables model discovery for llama.cpp/Ollama without auth

**Key Ideas:**
- Gateway model picker skipped live model discovery for custom providers unless `api_key` was configured
- Local providers (llama.cpp, Ollama) typically don't require auth on `/models`
- One-line fix: `if api_url and api_key:` → `if api_url:`
- Brings gateway picker into parity with CLI's `_model_flow_named_custom`

**Implementation Notes:**
- File: `hermes_cli/model_switch.py`
- Critical for anyone running local inference servers

---

### PR #26960 — `feat(agent): add ClaudeLocalClient subprocess shim for Claude Max OAuth accounts`
**Labels:** type/feature, comp/agent, provider/anthropic  
**Impact:** MEDIUM — enables Claude Max subscription users to use tools

**Key Ideas:**
- Subprocess-based adapter that shells out to official `claude` CLI binary
- Translates between Hermes's internal message format and CLI's stdin/stdout protocol
- CLI handles OAuth token refresh and tool-use authorization natively
- Bypasses third-party classifier that rejects direct API requests with tools
- Opt-in when `claude` binary is available and account has no overage credits

**Implementation Notes:**
- `agent/claude_local_client.py`: `ClaudeLocalClient` class
- Related PRs: #6427 (CLI subprocess transport), #26634 (cli-shim RFC for claude/codex/gemini CLIs)
- Pattern could be extended to other CLI-based providers

---

### PR #26940 — `feat: add Grok Build CLI provider`
**Labels:** type/feature, comp/agent, comp/cli, provider/xai  
**Impact:** MEDIUM — adds local Grok Build CLI as first-class provider

**Key Ideas:**
- Registers `grok-build` in provider registry, model catalog, aliases, model picker, runtime resolver
- `GrokCliClient`: OpenAI-compatible shim around `grok --prompt-file` for headless turns
- Defaults: `--no-memory --disable-web-search --max-turns 1 --output-format plain --effort xhigh`
- Supports env vars: `HERMES_GROK_BUILD_COMMAND`, `GROK_CLI_PATH`, `HERMES_GROK_BUILD_ARGS`
- Sets 512k context metadata for CLI transport

**Implementation Notes:**
- Relies on already-authenticated local Grok Build CLI session (`grok login`)
- Complementary to xAI OAuth provider (#25968) — different transport and model surface

---

### PR #26998 — `feat(auxiliary): add configurable fallback chains for auxiliary tasks`
**Labels:** type/feature, comp/agent  
**Impact:** HIGH — enables resilient multi-provider setups for vision/compression/TTS

**Key Ideas:**
- New config key: `auxiliary.<task>.fallback_chain` — list of `{provider, model, base_url?, api_key?}` entries
- When configured provider fails (quota, rate-limit, connection), automatically tries alternatives
- Previously fallback only worked with `resolved_provider: "auto"` — explicit providers got zero recovery
- Task-agnostic: works for ALL auxiliary tasks (vision, tts, compression, web_extract, etc.)

**Config Example:**
```yaml
auxiliary:
  vision:
    provider: glm
    model: glm-4v-flash
    fallback_chain:
      - provider: openrouter
        model: google/gemini-3-flash-preview
      - provider: nous
        model: claude-sonnet-4
```

---

### PR #27025 — `feat(models): add model_allowlist filter for dynamic-discovery providers`
**Labels:** type/feature, comp/cli, area/config  
**Impact:** MEDIUM — quality-of-life for users with many models (Ollama, OpenRouter)

**Key Ideas:**
- `model_allowlist` config option to filter model picker for dynamic-discovery providers
- Case-insensitive matching with `.lower().strip()` normalization
- Applied at both live discovery and static fallback paths
- Graceful degradation: if config is broken, show all models

---

## 💾 Memory System Enhancements

### PR #26946 — `feat(codex): expose memory and session search in MCP shim`
**Labels:** type/feature, comp/agent, comp/acp, tool/memory  
**Impact:** HIGH — enables Codex subprocesses to access Hermes memory

**Key Ideas:**
- Exposes `memory` and `session_search` through `codex_app_server` MCP shim
- Uses local stateless wrappers (not `handle_function_call` which blocks these tools)
- `memory`: creates short-lived `MemoryStore`, loads `MEMORY.md`/`USER.md`
- `session_search`: delegates to existing session search tool via `HERMES_HOME`
- Keeps truly stateful tools (`delegate_task`, `todo`) out of MCP surface

**Implementation Notes:**
- `agent/transports/hermes_tools_mcp_server.py`: adds to `EXPOSED_TOOLS`
- Stateless dispatchers via `_STATELESS_AGENT_LOOP_DISPATCHERS` dict
- Profile memory writes verified in tests

---

### PR #27043 — `fix(memory): gate Hindsight retention metadata`
**Labels:** type/feature, comp/plugins, tool/memory  
**Impact:** MEDIUM — prevents eval/benchmark noise from polluting memory

**Key Ideas:**
- Adds Hindsight retain metadata: `observed_at`, `memory_type`, `decay_hint`, `session_type`
- Blocks Hindsight retain by default for `eval/bench/benchmark` session types
- Adds configurable `memory_type` allow/deny gates for retained memories
- Preserves normal session behavior by default

---

## 🌊 Streaming & Voice

### PR #27040 — `feat(gateway): add generic voice_server gateway platform`
**Labels:** type/feature, comp/gateway, tool/tts  
**Impact:** HIGH — enables real-time voice interaction with Hermes

**Key Ideas:**
- Generic `voice_server` gateway platform over WebSocket protocol
- Voice runtime owns: audio transport, STT, TTS, turn-taking, barge-in, playback state
- Hermes owns: gateway routing, session persistence, agent turns, auth, history reconciliation
- **Partial streaming**: sanitized assistant text deltas sent to voice runtime as model emits them — TTS starts before full response generated
- Spoken-history reconciliation: tracks what user actually heard vs what was generated
- Supports inbound calls (fresh sessions) and outbound call protocol
- Compatible with Pipecat/Livekit or any WebSocket-based voice runtime

**Implementation Notes:**
- `gateway/platforms/voice_server.py`: WebSocket adapter (~994 lines)
- `voice_turn_id` minted once per streamed turn, flows on every `assistant_llm_*` event
- `assistant_spoken` reconciliation: replaces/deletes assistant content based on what was actually spoken
- Env config: `VOICE_SERVER_ROOM_URL`, `VOICE_SERVER_ROOM_ID`, `VOICE_SERVER_ALLOWED_USERS`

---

## 🗜️ Context Compression & Security

### PR #26981 — `Prevent todo snapshot injection after compression`
**Labels:** type/security, comp/agent, P2  
**Impact:** HIGH — closes prompt injection vector

**Key Ideas:**
- Removes post-compression todo snapshot injection as synthetic `user` message
- Previously, todo store content (which could contain attacker-controlled text) was injected with high semantic weight after compression
- Keeps todo state in in-memory `TodoStore` — agent accesses via tools, not injection
- Also adds `eval $(curl/wget)` command substitution detection to approval system

**Implementation Notes:**
- `run_agent.py`: removes 4 lines that appended `todo_snapshot` to compressed messages
- Regression test verifies malicious todo content doesn't appear in compressed output
- Fixes #26979

---

### PR #26956 — `fix: make compression status messages configurable`
**Labels:** type/feature, comp/agent, area/config  
**Impact:** LOW-MEDIUM — reduces noise for gateway users

**Key Ideas:**
- New config: `compression.status_messages` (default `true`)
- Suppresses duplicate compression lifecycle banners (preflight + generic)
- Users can disable compression status messages without disabling compression itself

---

## 🔧 Plugin & Skill System

### PR #26991 — `feat(plugins): add pre_goal_continuation hook for /goal veto`
**Labels:** type/feature, comp/cli, comp/gateway, comp/plugins  
**Impact:** MEDIUM — enables plugins to control goal continuation behavior

**Key Ideas:**
- New `pre_goal_continuation` hook fires after goal judge evaluates
- Plugins can veto continuation (return `{"action": "pause", "reason": "..."}`)
- First callback returning `"pause"` wins; remaining callbacks still run for side-effects
- Failure path (no plugin, callback raises) is swallowed and treated as "proceed"
- No changes to `GoalManager.evaluate_after_turn` semantics

---

### PR #26953 — `feat(cron): add pre-execution condition check for cron tasks`
**Labels:** type/feature, comp/cron  
**Impact:** MEDIUM — enables conditional cron execution without LLM cost

**Key Ideas:**
- Optional `condition` field on cron jobs — script evaluated before each tick
- Non-zero exit = skip (no execution, no delivery, no LLM cost)
- Exit 0 = proceed normally
- Example: `condition: is-workday.sh` to skip weekend briefings

```yaml
cron:
  - name: daily_briefing
    schedule: "0 9 * * *"
    condition: is-workday.sh
    prompt: "Generate daily briefing"
```

---

### PR #27034 — `feat(acp): add session edit auto-approval modes`
**Labels:** type/feature, comp/tools, comp/acp, P2  
**Impact:** MEDIUM — enables auto-approval of file edits in ACP sessions

**Key Ideas:**
- Three modes: `Default` (ask), `Accept Edits` (workspace-scoped auto-approve), `Don't Ask` (session-wide)
- Sensitive path detection: `.git`, `.ssh`, `.env`, credentials files always require approval
- Workspace mode auto-approves edits within project root and `/tmp/`
- Shows structured edit diff on tool-start card for auto-approved edits
- Pre-execution approval gate (not post-execution)

---

## 🌐 Gateway & Platform Integrations

### PR #26983 — `fix(gateway): /stop and /interrupt bypass steer/queue to always interrupt agent`
**Labels:** type/bug, comp/gateway, P1  
**Impact:** HIGH — fixes critical UX bug on all gateway platforms

**Key Ideas:**
- `/stop`, `/interrupt`, `/cancel` now bypass `busy_input_mode` steer/queue to force interrupt
- Previously these commands were fed to `running_agent.steer()` or queued — agent treated them as context text
- Supports: slash-prefixed, plain text (Feishu compat), `@mention` suffix (group chats)
- Only first token is checked — "please stop" follows normal steer/queue semantics

---

### PR #26901 — `feat(mattermost): add ambient session ingestion mode`
**Labels:** type/feature, comp/gateway  
**Impact:** MEDIUM — enables passive memory accumulation without triggering LLM

**Key Ideas:**
- New `MATTERMOST_AMBIENT_CHANNELS` env var
- Messages stored silently with sender attribution — no LLM response
- On @mention, LLM runs with full accumulated context
- Prevents response loops in multi-agent environments
- Adds `trigger_llm: bool` field to `MessageEvent` in base platform

---

### PR #27058 — `feat(cli): display RTK token savings in status bar`
**Labels:** (none)  
**Impact:** LOW-MEDIUM — proof-of-concept for status bar extensibility

**Key Ideas:**
- Shows RTK (prompt caching) token savings in CLI status bar: `⟡ 432K/21%`
- Direct SQLite read of RTK's tracking DB with 5-second cache
- **Proposes status bar plugin API** (Option B) — plugins register named fragments
- Any plugin could add to status bar (disk-cleanup, achievements, etc.)

---

### PR #27060 — `fix(mcp): prevent parallel-safe prefix collisions`
**Labels:** (none)  
**Impact:** MEDIUM — fixes correctness bug in MCP tool routing

**Key Ideas:**
- Tracks exact MCP tool-to-server provenance when tools are registered
- Uses exact server provenance for `supports_parallel_tool_calls` checks instead of prefix parsing
- Fixes ambiguous names like `mcp_a_b_tool` (could match server `a` or `a_b`)

---

## Summary: Top Picks for Local/CLI Usage

| Priority | PR | Why It Matters |
|----------|-----|----------------|
| ⭐⭐⭐ | #27042 | Enables model discovery for local providers without API key |
| ⭐⭐⭐ | #26905 | 2-3x turn reduction for automated workloads via cache-stable mode |
| ⭐⭐⭐ | #26998 | Configurable fallback chains — resilient multi-provider setups |
| ⭐⭐⭐ | #26946 | Memory/session search exposed to MCP subprocesses |
| ⭐⭐ | #26908 | Budget pressure hints reduce runaway agent loops |
| ⭐⭐ | #27045 | Better context compression fallback prevents overflow |
| ⭐⭐ | #26960 | Claude CLI subprocess shim — pattern for any CLI-based provider |
| ⭐⭐ | #26940 | Grok Build CLI provider — another local CLI backend |
| ⭐⭐ | #27040 | Voice server gateway — real-time streaming architecture |
| ⭐ | #27025 | Model allowlist for cleaner picker with many local models |
| ⭐ | #26981 | Security: prevents todo injection after compression |
| ⭐ | #27060 | MCP tool routing correctness fix |
