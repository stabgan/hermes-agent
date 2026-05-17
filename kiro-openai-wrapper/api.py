"""OpenAI-compatible API wrapper around kiro-cli.

Drop this file into any FastAPI project to expose kiro-cli
as a standard /v1/chat/completions endpoint.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import uuid
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

# ─── Configuration ───────────────────────────────────────────────────────────

# Path to kiro-cli binary
KIRO_CLI = os.environ.get("KIRO_CLI_PATH", os.path.expanduser("~/.local/bin/kiro-cli"))

# Agent to use (set to None for no agent)
AGENT_NAME = os.environ.get("KIRO_AGENT", None)

# System prompt prepended to all requests (set to "" to disable)
SYSTEM_CONTEXT = os.environ.get("KIRO_SYSTEM_PROMPT", "")

# ─── Models ──────────────────────────────────────────────────────────────────

AVAILABLE_MODELS = [
    {"id": "auto", "object": "model", "created": 1700000000, "owned_by": "kiro", "context_window": 1000000},
    {"id": "claude-opus-4.6", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 1000000},
    {"id": "claude-sonnet-4.6", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 1000000},
    {"id": "claude-opus-4.5", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 200000},
    {"id": "claude-sonnet-4.5", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 200000},
    {"id": "claude-sonnet-4", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 200000},
    {"id": "claude-haiku-4.5", "object": "model", "created": 1700000000, "owned_by": "anthropic", "context_window": 200000},
    {"id": "deepseek-3.2", "object": "model", "created": 1700000000, "owned_by": "deepseek", "context_window": 164000},
    {"id": "minimax-m2.5", "object": "model", "created": 1700000000, "owned_by": "minimax", "context_window": 196000},
    {"id": "minimax-m2.1", "object": "model", "created": 1700000000, "owned_by": "minimax", "context_window": 196000},
    {"id": "glm-5", "object": "model", "created": 1700000000, "owned_by": "zhipu", "context_window": 200000},
    {"id": "qwen3-coder-next", "object": "model", "created": 1700000000, "owned_by": "alibaba", "context_window": 256000},
]

# ─── Request/Response Models ─────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "claude-sonnet-4.6"
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def strip_ansi(text: str) -> str:
    """Remove ALL ANSI escape codes."""
    text = re.sub(r"\x1b\[[\d;]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b\[\?[\d;]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b\][\d;]*[^\x07]*\x07", "", text)
    text = re.sub(r"\x1b[^[\]](.|$)", "", text)
    return text


def is_metadata(line: str) -> bool:
    """Check if a line is kiro-cli metadata."""
    s = line.strip()
    if not s:
        return False
    if s[0] in "📷⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏":
        return True
    if s.startswith("▸ Time:") or s.startswith(" ▸ Time:"):
        return True
    if any(x in s for x in ("using tool:", "Searching for", "No symbols found",
                             "Completed in", "Looking up", "Reading file",
                             "Reading ", "Running", "Executing")):
        return True
    if s.startswith("/Users/") or "(scoped to:" in s:
        return True
    if re.match(r"^\[\d+(\.\d+)?\]$", s):
        return True
    if "[2K" in s or "[1G" in s or "[?25" in s:
        return True
    return False


def build_prompt(messages: list[ChatMessage]) -> str:
    """Convert OpenAI messages to a prompt string for kiro-cli."""
    parts = []

    if SYSTEM_CONTEXT:
        parts.append(SYSTEM_CONTEXT)

    system_msgs = [m for m in messages if m.role == "system"]
    user_assistant_msgs = [m for m in messages if m.role != "system"]

    if system_msgs:
        parts.append(f"[System: {system_msgs[-1].content}]")

    for msg in user_assistant_msgs:
        label = "User" if msg.role == "user" else "Assistant"
        parts.append(f"{label}: {msg.content}")

    if user_assistant_msgs and user_assistant_msgs[-1].role == "user":
        parts.append("\nAssistant:")

    return "\n\n".join(parts)


def build_command(model: str) -> list[str]:
    """Build the kiro-cli command."""
    cmd = [KIRO_CLI, "chat", "--no-interactive", "--model", model,
           "--trust-all-tools", "--wrap", "never"]
    if AGENT_NAME:
        cmd.extend(["--agent", AGENT_NAME])
    return cmd


def clean_output(raw: str) -> str:
    """Clean kiro-cli output: strip ANSI, remove metadata, strip '> ' prefix."""
    clean = strip_ansi(raw)
    lines = clean.split("\n")
    result = []
    for line in lines:
        if line.startswith("> "):
            line = line[2:]
        if is_metadata(line):
            continue
        if any(x in line for x in ("All tools are now trusted", "Agents can sometimes",
                                    "Learn more at", "Checkpoints are enabled",
                                    "kiro.dev/docs", "understand the risks")):
            continue
        result.append(line)
    return "\n".join(result).strip()


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("/v1/models")
async def list_models():
    return {"object": "list", "data": AVAILABLE_MODELS}


@router.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    model = request.model if request.model in [m["id"] for m in AVAILABLE_MODELS] else "claude-sonnet-4.6"
    prompt = build_prompt(request.messages)

    if request.stream:
        return StreamingResponse(
            stream_response(prompt, model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        return await non_streaming_response(prompt, model)


async def non_streaming_response(prompt: str, model: str) -> dict:
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    try:
        result = subprocess.run(
            build_command(model), input=prompt,
            capture_output=True, text=True, timeout=180,
        )
        content = clean_output(result.stdout)
        if not content:
            content = "Ready. How can I help?"
    except subprocess.TimeoutExpired:
        content = "Response timed out."
    except Exception as e:
        content = f"Error: {str(e)[:100]}"

    return {
        "id": completion_id, "object": "chat.completion",
        "created": int(time.time()), "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": len(content.split()), "total_tokens": len(prompt.split()) + len(content.split())},
    }


async def stream_response(prompt: str, model: str) -> AsyncGenerator[str, None]:
    import fcntl

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())

    def make_chunk(text):
        return f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': text}, 'finish_reason': None}]})}\n\n"

    try:
        process = subprocess.Popen(
            build_command(model), stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=False,
        )
        process.stdin.write(prompt.encode("utf-8"))
        process.stdin.close()

        # Non-blocking stdout
        fd = process.stdout.fileno()
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        buffer = ""
        while True:
            retcode = process.poll()
            try:
                raw = process.stdout.read(4096)
                if raw:
                    buffer += raw.decode("utf-8", errors="replace")
                elif retcode is not None:
                    break
                else:
                    import time as _t; _t.sleep(0.05); continue
            except (BlockingIOError, IOError):
                if retcode is not None: break
                import time as _t; _t.sleep(0.05); continue

            while "\n" in buffer:
                nl = buffer.find("\n")
                line = buffer[:nl]
                buffer = buffer[nl + 1:]

                line = strip_ansi(line)
                if line.startswith("> "):
                    line = line[2:]
                if is_metadata(line.strip()):
                    continue
                if any(x in line for x in ("All tools are now trusted", "Agents can sometimes",
                                            "Learn more at", "Checkpoints are enabled")):
                    continue

                yield make_chunk(line + "\n")

        if buffer.strip():
            remaining = strip_ansi(buffer)
            if remaining.startswith("> "): remaining = remaining[2:]
            if remaining.strip() and not is_metadata(remaining.strip()):
                yield make_chunk(remaining)

        process.wait(timeout=10)

        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'id': completion_id, 'object': 'chat.completion.chunk', 'created': created, 'model': model, 'choices': [{'index': 0, 'delta': {'content': f'Error: {str(e)[:50]}'}, 'finish_reason': 'stop'}]})}\n\n"
        yield "data: [DONE]\n\n"
