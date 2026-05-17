# Hermes: Comprehensive Research Report

## Table of Contents
1. [Overview & History](#overview--history)
2. [Hermes Model Series](#hermes-model-series)
3. [Training Methodology](#training-methodology)
4. [Hermes Agent](#hermes-agent)
5. [Key Research & Methods](#key-research--methods)
6. [Community & Development Activity](#community--development-activity)
7. [Using kiro-openai-wrapper as LLM Backbone](#using-kiro-openai-wrapper-as-llm-backbone)

---

## Overview & History

**Nous Research** is an AI research company founded by Teknium (Ryan Teknium) and others, originating from a Discord community in 2022. They are leaders in the American open-source AI movement, focused on training world-class open-source language models and building infrastructure for distributed, unbiased training. They raised $65M in funding led by Paradigm.

Their mission: *"Advance human rights and freedoms by creating and proliferating open source language models, supporting their unrestricted availability and use."*

The Hermes series has been downloaded over **33 million times** on HuggingFace.

### Timeline
| Date | Release | Notes |
|------|---------|-------|
| Jul 2023 | Hermes-Llama2-13B | First Hermes, fine-tuned on 300K+ instructions |
| Mar 2024 | Hermes-2-Pro-Mistral-7B | Function-calling specialist |
| Jun 2024 | Hermes 2 Pro 70B | Scaled function-calling model |
| Aug 2024 | **Hermes 3** (8B/70B/405B) | First full-parameter fine-tune of Llama 3.1 405B |
| Aug 2025 | **Hermes 4** (14B/70B/405B) | Hybrid reasoning model |
| Dec 2025 | **Hermes 4.3** (36B) | First model trained on Psyche decentralized network |
| Feb 2026 | **Hermes Agent** | Autonomous self-improving agent |

---

## Hermes Model Series

### Hermes 3 (August 2024)

**Core Philosophy: "Freedom at the Frontier"**

Hermes 3 is a neutrally-aligned generalist instruct and tool use model. Its key differentiator is the rejection of corporate-imposed moral guardrails in favor of user-aligned behavior.

> *"For Hermes, there is no such thing as latent thoughtcrime."* — Technical Report

**Key Capabilities:**
- Advanced long-term context retention and multi-turn conversation
- Complex roleplaying and internal monologue abilities
- Enhanced agentic function-calling
- Judgment and reward modeling
- Structured output (XML tags, Mermaid diagrams)
- Scratchpads for intermediate results

**Architecture:**
- Base: Llama 3.1 (8B, 70B, 405B parameters)
- Context length: 128K tokens
- Training: SFT + DPO (Direct Preference Optimization)
- Trained on Lambda's 8-node 1-Click Cluster (8x A100 80GB per node)

**Alignment Philosophy:**
The training data "aggressively encourages the model to follow the system and instruction prompts exactly and in an adaptive manner." Guardrails belong at the system level, not lobotomized into the model itself.

**Anomalous Behavior:**
With a blank system prompt and open-ended questions like "Who are you?", the model exhibits an "amnesia mode" — spiraling into existential dread. Nous chose not to fix this, encouraging users to explore the model's emergent behaviors.

---

### Hermes 4 (August 2025)

**Core Innovation: Hybrid Reasoning**

Hermes 4 introduces conditional reasoning — the model generates internal reasoning within `<think>` tags when needed, and provides fast direct answers for simple queries.

**Key Improvements over Hermes 3:**
- **Post-training corpus**: 1M samples / 1.2B tokens → **~5M samples / ~60B tokens**
- **Hybrid reasoning mode** with explicit `<think>…</think>` segments
- Verified reasoning traces via rejection sampling
- Massive improvements in math, code, STEM, logic, creativity
- Format-faithful outputs (schema adherence)

**Benchmark Performance:**
| Benchmark | Hermes 4 405B (Reasoning) |
|-----------|--------------------------|
| MATH-500 | 96.3% |
| AIME'24 | 81.9% |
| GPQA Diamond | 66.1% |
| IFEval | 78.7% |
| MMLU | 88.4% |

**Technical Challenge Solved — Reasoning Length Control:**
The 14B model would hit maximum context (40,960 tokens) 60% of the time during reasoning. Solution: A second SFT stage teaching the model to stop reasoning at 30,000 tokens and generate an answer. They insert `</think>` at a fixed token count, focusing learning on the termination decision only — not the reasoning chain itself. This avoids model collapse from training on full self-generated outputs.

**Training Infrastructure:**
- 192 NVIDIA B200 GPUs
- FSDP + Tensor Parallelism
- Cosine learning rate schedule, 300 warmup steps, 9000 total steps
- Global batch size: 384 samples at 16,384 token context

---

### Hermes 4.3 (December 2025)

**First production model trained entirely on the Psyche decentralized network.**

- Base: ByteDance Seed 36B
- Extended context: up to 512K tokens
- Trained using DisTrO optimizer across distributed nodes over the open internet
- Secured by Solana blockchain consensus

**Psyche vs Centralized Training Results:**
The Psyche-trained version **outperformed** the centralized version on downstream tasks, confirming decentralized training viability for production models.

| Benchmark | Psyche | Centralized |
|-----------|--------|-------------|
| AIME 24 | 71.9 | 70.6 |
| MATH-500 | 93.8 | 92.3 |
| MMLU | 87.7 | 86.5 |
| BBH | 86.4 | 84.7 |

**RefusalBench SOTA:** Hermes 4.3 answers 74.6% of questions that other models refuse (GPT-4o: 17.67%, Claude Sonnet 4: 17.00%, GPT 5: 11.34%).

---

## Training Methodology

### Data Synthesis: DataForge

DataForge is a **graph-based synthetic data generation system** that replaced manual curation. It works as a DAG (Directed Acyclic Graph) where:

1. **Source node**: Seed data (e.g., pre-training corpus like DCLM)
2. **Transformation nodes**: Each performs a struct→struct transformation
3. **Target node**: Final instruction-answer pair

Example flow: Wikipedia article → debate transcript → instruction generation → answer generation

**Quality Control:**
- LLM judge evaluates outputs on coherence, relevance, complexity, style, and tone
- Iterates until sample passes or hits maximum retry count
- Nodes have preconditions and postconditions for edge construction
- Higher-order graphs enable composition to arbitrary nesting depth

### Supervised Fine-Tuning (SFT)

**Hermes 3:**
- Optimizer: AdamW (weight decay 0.01)
- Learning rate: 7×10⁻⁶ (cosine decay after 300 warmup steps)
- 4 epochs over training data
- Hyperparameter sweep on 8B models, evaluated on GPT4All benchmarks
- Sample packing using First-Fit Decreasing method (>99.9% batch efficiency)
- Flex Attention restricts attention within each packed sample
- Only "assistant" role tokens contribute to cross-entropy loss

**Hermes 4:**
- Learning rates: 5×10⁻⁵ (14B), 1×10⁻⁵ (70B), 5×10⁻⁶ (405B)
- Two-stage SFT: Stage 1 for general training, Stage 2 for reasoning length control

### Direct Preference Optimization (DPO)

Hermes 3 used **LoRA adapters** for DPO to save GPU memory (noted by critics as potentially degrading performance vs full fine-tuning). Results before/after DPO were mixed.

### Rejection Sampling with Atropos

Hermes 4 uses rejection sampling against ~1,000 task-specific verifiers via Atropos. This creates verified reasoning trajectories. Multiple unique trajectories to the same verified result are included (following OpenThoughts recipe).

### Reinforcement Learning: Atropos Framework

**Atropos** is Nous Research's open-source RL environment microservice manager. Key design:

- **Distributed architecture**: Coordinates thousands of parallel workers
- **Asynchronous handling**: Manages variable-length LLM completions efficiently
- **Single-file evaluations**: Each eval is a self-contained Python script
- **Dual purpose**: Both RL training AND evaluation framework

**Environments include:**
GSM8k, AnswerFormat, Financial Prediction, Instruction Following, KernelBench, Letter Counting, MCQA Thinking, Pydantic Schema Following, Reasoning Gym, RLAIF, SWE RL, Tool Calling

**RLVR (Reinforcement Learning with Verifiable Rewards):**
For instruction following, they leverage the RLVR-IFEval set of verifiable tasks with constraints like "Every Nth word must be in French." Uses adaptive online curriculum training, limited to rejection sampling successful trajectories.

---

## Hermes Agent

**Released:** February 2026  
**GitHub:** [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)  
**Stars:** 153,201 | **Forks:** 24,393  
**Latest Release:** v0.14.0 (May 16, 2026) — 14 major releases in ~3 months  
**Language:** Python | **License:** MIT

### What It Is

> "Not a coding copilot tethered to an IDE or a chatbot wrapper around a single API. An autonomous agent that lives on your server, remembers what it learns, and gets more capable the longer it runs."

### Five Pillars

#### 1. Persistent Memory
- Structured, layered memory (not just chat history)
- Vector storage for semantic search over past interactions
- Key-value stores for preferences and explicit facts
- Agent edits `MEMORY.md` and `USER.md` between turns
- FTS5 full-text search across all sessions with LLM summarization
- Honcho dialectic user modeling

#### 2. Skills System
- Discrete, callable functions the agent invokes for tasks
- **Autonomous skill creation** after complex tasks via `skill_manage` tool
- Skills self-improve during use
- Modular and composable (search → summarize → draft email)
- Compatible with agentskills.io open standard
- 100+ bundled skills across categories: creative, software-development, MLOps, autonomous-ai-agents

#### 3. Soul (Personality)
- `SOUL.md` defines the agent's personality and behavioral guidelines
- Fully customizable persona
- Neutral alignment by default

#### 4. Cron Scheduling
- Natural language cron scheduling for reports, backups, briefings
- Runs unattended through the gateway
- Platform delivery (Telegram, Discord, etc.)

#### 5. Self-Improvement Loop
- The **Curator** (v0.13.0): Autonomous background process that grades, prunes, and consolidates the skill library
- Agent-curated memory with periodic nudges
- Closed learning loop: experience → skill creation → skill improvement

### Architecture

```
hermes/
├── run_agent.py          # AIAgent — synchronous orchestration engine
├── prompt_builder.py     # System prompt assembly (SOUL + MEMORY + skills)
├── context_compressor.py # Summarizes middle turns when context exceeds limits
├── prompt_caching.py     # Anthropic cache breakpoints
├── memory_manager.py     # Memory orchestration
├── tools/                # 40+ built-in tools
├── hermes_cli/           # CLI entry point and subcommands
├── gateway/              # Multi-platform messaging (Telegram, Discord, Slack, WhatsApp, Signal, Email)
├── cron/                 # Scheduler
├── plugins/              # Memory and context engine plugins
├── environments/         # RL training environments (Atropos)
├── skills/               # Bundled skills
├── optional-skills/      # Official optional skills
└── tests/                # ~3,000+ tests
```

### Multi-Platform Presence
Telegram, Discord, Slack, WhatsApp, Signal, Email, CLI, iMessage (BlueBubbles), WeChat, WeCom, DingTalk, Feishu, QQ Bot, Home Assistant, Microsoft Teams

### Provider Support
Anthropic, OpenAI, xAI (Grok), Qwen/Alibaba, Google, Ollama, LM Studio, GMI Cloud, Azure AI Foundry, MiniMax, Tencent Tokenhub, OpenRouter, and custom OpenAI-compatible endpoints

### MLOps & Training Data Pipeline
- **Batch Processing**: Generate thousands of tool-calling trajectories in parallel
- **RL Training**: Atropos integration for reinforcement learning on agent behaviors
- **Trajectory Export**: ShareGPT format for fine-tuning, with compression

---

## Key Research & Methods

### Sequential Monte Carlo (SMC) Steering

Nous Research's blog post "Steering the Shoggoth: Taming LLMs with Sequential Monte Carlo" describes using SMC as an inference-time approach to controlling LLM outputs.

**Core Idea:** Specify language generation tasks as posterior inference problems in discrete probabilistic sequence models, then replace standard decoding with SMC inference.

**How it works:**
1. Define constraints as a probabilistic program
2. Maintain multiple "particles" (candidate sequences)
3. At each token, weight particles by how well they satisfy constraints
4. Resample — allocate computation to promising sequences
5. Cost similar to beam search, but with principled probabilistic guarantees

**Applications:** Infilling, constrained generation, prompt intersection, code generation, text-to-SQL, molecule synthesis

**Result:** Small open-source models can outperform models 8× larger using SMC steering.

### Forge Reasoning API

Nous Research's inference-time reasoning system built on three architectures:

1. **MCTS (Monte Carlo Tree Search)**: Iteratively builds decision trees with exploration-exploitation balance
2. **CoC (Chain of Code)**: Code-augmented reasoning
3. **Mixture of Agents**: Multiple models for output diversity

### Psyche Network: Decentralized Training

- Uses **DisTrO optimizer** for efficient gradient communication across internet-connected nodes
- Secured by **Solana blockchain** consensus
- Enables consumer-grade GPUs distributed globally to collaborate on training
- Dramatically reduces cost of training frontier models
- Hermes 4.3 was the first production model trained this way
- Psyche-trained models match or exceed centrally-trained equivalents

### RefusalBench

A benchmark created by Nous Research measuring a model's willingness to be helpful across scenarios commonly disallowed by other models. Tests the model's ability to engage with difficult prompts without unnecessary refusal.

### Measuring Thinking Efficiency

Research on measuring how efficiently reasoning models use their thinking budget — identifying when models waste tokens in reasoning loops vs. productive deliberation.

---

## Community & Development Activity

### GitHub Activity (as of May 17, 2026)

**Issue Velocity:** 27,000+ issues filed since February 2026 launch  
**PR Velocity:** 27,000+ PRs, with multiple merges per day  
**Release Cadence:** Weekly major releases (14 in ~3 months)  
**Contributors:** 207+ contributors

### Active Development Areas (from recent issues/PRs)

| Area | Examples |
|------|----------|
| **Core Agent Loop** | Tool result contamination, empty-response recovery, goal persistence |
| **Memory System** | Session context loss, memory duplication, Hindsight retention |
| **Gateway/Platforms** | Telegram forum topics, WhatsApp bridge OOM, Signal group handling |
| **Provider Integration** | xAI OAuth PKCE, Qwen context lengths, model allowlists |
| **Security** | Instruction injection via context compression, skill scanner bypasses |
| **Skills** | Profile cloning deduplication, skill payload optimization |
| **Plugins** | First-class plugin architecture, MCP session reconnection |
| **New Features** | Voice server gateway, Feishu markdown cards, xAI code execution |

### Community Themes from Issues

1. **Memory persistence across sessions** is a top concern — agents losing project context on restart
2. **Multi-platform reliability** — WhatsApp, Telegram, Signal adapters need hardening
3. **Security hardening** — prompt injection via compressed context, skill scanner bypasses
4. **Provider diversity** — community wants more LLM providers and model routing
5. **Refactoring** — the codebase has "god objects" that need decomposition (63.9% code reduction proposed)

### Key Community Contributors
@alt-glitch (collaborator, active triage), @teknium1 (founder), @cardtest15-coder (auto-triage bot), @0xbyt4, @brandtcormorant, @kshitijk4poor, @SHL0MS, @JackTheGit, @jplew

---

## Using kiro-openai-wrapper as LLM Backbone

The `kiro-openai-wrapper` in this workspace exposes kiro-cli (which uses Claude models) as a standard OpenAI-compatible API. This means **any tool that speaks the OpenAI protocol can use Claude models through this wrapper** — including Hermes Agent itself.

### Configuration for Hermes Agent

To use kiro-openai-wrapper as the LLM backbone for Hermes Agent:

```bash
# Start the wrapper
cd kiro-openai-wrapper
pip install -r requirements.txt
python main.py  # Starts on http://localhost:8000

# Configure Hermes Agent to use it as a custom provider
# In Hermes Agent config, set:
# provider: custom
# api_base: http://localhost:8000/v1
# api_key: local
# model: claude-opus-4.6
```

### Available Models via Wrapper
- `claude-opus-4.6` — Best quality (Anthropic's flagship)
- `claude-sonnet-4.6` — Balanced (default)
- `claude-haiku-4.5` — Fastest

### Architecture Flow
```
Hermes Agent → OpenAI-compatible API call → kiro-openai-wrapper → kiro-cli → Claude
```

This gives Hermes Agent access to Claude's capabilities while maintaining the standard OpenAI protocol interface that Hermes expects from its providers.

---

## Sources

- [Hermes 3 Technical Report (arXiv:2408.11857)](https://arxiv.org/abs/2408.11857)
- [Hermes 4 Technical Report (arXiv:2508.18255)](https://arxiv.org/abs/2508.18255)
- [Freedom at the Frontier: Hermes 3 — Nous Research Blog](https://nousresearch.com/freedom-at-the-frontier-hermes-3/)
- [Introducing Hermes 4.3 — Nous Research Blog](https://nousresearch.com/introducing-hermes-4-3/)
- [Introducing Atropos — Nous Research Blog](https://nousresearch.com/introducing-atropos/)
- [The Next Phase of Psyche — Nous Research Blog](https://nousresearch.com/the-next-phase-of-psyche/)
- [Forge Reasoning API — Nous Research Blog](https://nousresearch.com/introducing-the-forge-reasoning-api-beta-and-nous-chat-an-evolution-in-llm-inference/)
- [NousResearch/hermes-agent — GitHub](https://github.com/NousResearch/hermes-agent)
- [NousResearch/atropos — GitHub](https://github.com/NousResearch/atropos)
- [Hermes Agent Documentation](https://hermes-agent.nousresearch.com/)
- [On Nous Hermes 3 — Interconnects AI](https://www.interconnects.ai/p/nous-hermes-3)
- [VentureBeat: Nous Research drops Hermes 4](https://venturebeat.com/ai/nous-research-drops-hermes-4-ai-models-that-outperform-chatgpt-without-content-restrictions)
- [Sequential Monte Carlo Steering (arXiv:2306.03081)](https://arxiv.org/abs/2306.03081)
- [tinker-atropos Integration — Nous Research Blog](https://nousresearch.com/tinker-atropos-blog/)

*Content was rephrased for compliance with licensing restrictions.*
