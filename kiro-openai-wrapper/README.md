# kiro-openai-wrapper

Wraps `kiro-cli` as a standard OpenAI-compatible API. Any tool that speaks the OpenAI protocol can use Claude models through this.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Server starts at `http://localhost:8000`.

## Usage

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="local")

response = client.chat.completions.create(
    model="claude-opus-4.6",
    messages=[{"role": "user", "content": "Hello!"}],
    stream=True
)
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

## Configuration (environment variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `KIRO_CLI_PATH` | `~/.local/bin/kiro-cli` | Path to kiro-cli binary |
| `KIRO_AGENT` | None | Agent name (e.g., `interview-prep-coach`) |
| `KIRO_SYSTEM_PROMPT` | "" | System prompt prepended to all requests |

## Models

- `claude-opus-4.6` — Best quality
- `claude-sonnet-4.6` — Balanced (default)
- `claude-haiku-4.5` — Fastest

## Files

```
kiro-openai-wrapper/
├── main.py              # FastAPI app entry point
├── api.py               # The wrapper (self-contained, copy anywhere)
├── requirements.txt     # Dependencies
└── README.md            # This file
```

## Use with Open WebUI

```bash
docker run -d -p 3000:8080 \
  -e OPENAI_API_BASE_URL=http://host.docker.internal:8000/v1 \
  -e OPENAI_API_KEY=local \
  ghcr.io/open-webui/open-webui:main
```

## Use with a custom agent

```bash
KIRO_AGENT=my-agent python main.py
```

## Use with Hermes Agent

This wrapper serves as the LLM backbone for [Hermes Agent](https://github.com/stabgan/hermes-agent) in local-only mode.

```bash
# 1. Start the wrapper
python main.py

# 2. In another terminal, run Hermes Agent
# (configured to use http://localhost:8000/v1 as its provider)
hermes
```

See `../hermes-agent/kiro-local-config.yaml` for the full Hermes configuration.

### Architecture

```
User ↔ Hermes Agent (memory, skills, tools) ↔ kiro-openai-wrapper ↔ kiro-cli ↔ Claude
```

Hermes Agent handles the agentic layer (persistent memory, skill creation, tool execution, multi-platform presence) while kiro-cli provides the raw LLM inference locally.
