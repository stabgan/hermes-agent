"""Native kiro-cli provider for Hermes Agent.

Integrates kiro-cli directly as a first-class provider, bypassing the need
for the external OpenAI-compatible wrapper. Shells out to kiro-cli binary
and translates between Hermes's internal message format and kiro-cli's
stdin/stdout protocol.

This is the LOCAL-ONLY provider — no network calls, no API keys, no cloud.
All inference happens through the locally-installed kiro-cli binary.

Usage in config.yaml:
    provider: kiro-cli
    model: claude-opus-4.6

Or via environment:
    HERMES_PROVIDER=kiro-cli hermes
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from providers.base import ProviderProfile

logger = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

KIRO_CLI_DEFAULT_PATH = os.path.expanduser("~/.local/bin/kiro-cli")

KIRO_MODELS = [
    "auto",
    "claude-opus-4.6",
    "claude-sonnet-4.6",
    "claude-opus-4.5",
    "claude-sonnet-4.5",
    "claude-sonnet-4",
    "claude-haiku-4.5",
    "deepseek-3.2",
    "minimax-m2.5",
    "minimax-m2.1",
    "glm-5",
    "qwen3-coder-next",
]

# Context window sizes for kiro-cli models (tokens)
# Source: kiro-cli chat --list-models --format json
KIRO_CONTEXT_LENGTHS = {
    "auto": 1_000_000,
    "claude-opus-4.6": 1_000_000,
    "claude-sonnet-4.6": 1_000_000,
    "claude-opus-4.5": 200_000,
    "claude-sonnet-4.5": 200_000,
    "claude-sonnet-4": 200_000,
    "claude-haiku-4.5": 200_000,
    "deepseek-3.2": 164_000,
    "minimax-m2.5": 196_000,
    "minimax-m2.1": 196_000,
    "glm-5": 200_000,
    "qwen3-coder-next": 256_000,
}

# Max output tokens
KIRO_MAX_OUTPUT = {
    "auto": 32_000,
    "claude-opus-4.6": 32_000,
    "claude-sonnet-4.6": 32_000,
    "claude-opus-4.5": 16_000,
    "claude-sonnet-4.5": 16_000,
    "claude-sonnet-4": 16_000,
    "claude-haiku-4.5": 8_192,
    "deepseek-3.2": 16_000,
    "minimax-m2.5": 16_000,
    "minimax-m2.1": 16_000,
    "glm-5": 16_000,
    "qwen3-coder-next": 16_000,
}


# ─── ANSI / Metadata Stripping ───────────────────────────────────────────────

def _strip_ansi(text: str) -> str:
    """Remove ALL ANSI escape codes from kiro-cli output."""
    text = re.sub(r"\x1b\[[\d;]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b\[\?[\d;]*[A-Za-z]", "", text)
    text = re.sub(r"\x1b\][\d;]*[^\x07]*\x07", "", text)
    text = re.sub(r"\x1b[^[\]](.|$)", "", text)
    return text


def _is_metadata_line(line: str) -> bool:
    """Check if a line is kiro-cli metadata (spinners, tool output, etc.)."""
    s = line.strip()
    if not s:
        return False
    # Spinner characters
    if s[0] in "📷⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏":
        return True
    # Time/status lines
    if s.startswith("▸ Time:") or s.startswith(" ▸ Time:"):
        return True
    # Tool execution metadata (must START with these patterns)
    if s.startswith("using tool:") or s.startswith("Searching for "):
        return True
    if s.startswith("No symbols found") or s.startswith("Completed in "):
        return True
    if s.startswith("Looking up ") or s.startswith("Reading file:"):
        return True
    if s.startswith("Running tool ") or s.startswith("Executing "):
        return True
    # File paths and scoping
    if s.startswith("/Users/") or "(scoped to:" in s:
        return True
    # Timing markers
    if re.match(r"^\[\d+(\.\d+)?\]$", s):
        return True
    # Terminal control sequences
    if "[2K" in s or "[1G" in s or "[?25" in s:
        return True
    return False


_NOISE_PHRASES = frozenset({
    "All tools are now trusted",
    "Agents can sometimes",
    "Learn more at",
    "Checkpoints are enabled",
    "kiro.dev/docs",
    "understand the risks",
})


def _clean_kiro_output(raw: str) -> str:
    """Clean kiro-cli output: strip ANSI, remove metadata, strip '> ' prefix."""
    clean = _strip_ansi(raw)
    lines = clean.split("\n")
    result = []
    for line in lines:
        if line.startswith("> "):
            line = line[2:]
        if _is_metadata_line(line):
            continue
        if any(phrase in line for phrase in _NOISE_PHRASES):
            continue
        result.append(line)
    return "\n".join(result).strip()


# ─── Provider Profile ─────────────────────────────────────────────────────────

class KiroCliProfile(ProviderProfile):
    """Provider profile for native kiro-cli integration."""

    def __init__(self):
        super().__init__(
            name="kiro-cli",
            api_mode="chat_completions",  # We emulate chat completions
            aliases=("kiro", "kiro-local", "local-kiro"),
            display_name="kiro-cli (Local)",
            description="Local Claude inference via kiro-cli binary — no API key needed",
            signup_url="",
            env_vars=("KIRO_CLI_PATH",),
            base_url="http://localhost:8000/v1",  # Fallback to wrapper if available
            auth_type="api_key",
            supports_health_check=False,
            fallback_models=tuple(KIRO_MODELS),
        )

    def fetch_models(self, *, api_key: str | None = None, timeout: float = 8.0) -> list[str] | None:
        """Return available models — always returns the static list for kiro-cli."""
        return list(KIRO_MODELS)


# ─── kiro-cli Client ──────────────────────────────────────────────────────────

class KiroCliClient:
    """Subprocess-based client that shells out to kiro-cli for inference.

    Translates between Hermes's OpenAI-style message format and kiro-cli's
    stdin/stdout protocol. Handles streaming, tool calls, and error recovery.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4.6",
        kiro_cli_path: str | None = None,
        agent_name: str | None = None,
        timeout: int = 300,
    ):
        self.model = model
        self.kiro_cli_path = kiro_cli_path or os.environ.get(
            "KIRO_CLI_PATH", KIRO_CLI_DEFAULT_PATH
        )
        self.agent_name = agent_name or os.environ.get("KIRO_AGENT")
        self.timeout = timeout
        self._validate_binary()

    def _validate_binary(self) -> None:
        """Check that kiro-cli binary exists and is executable."""
        path = Path(self.kiro_cli_path)
        if not path.exists():
            raise FileNotFoundError(
                f"kiro-cli binary not found at {self.kiro_cli_path}. "
                f"Set KIRO_CLI_PATH environment variable or install kiro-cli."
            )
        if not os.access(str(path), os.X_OK):
            raise PermissionError(
                f"kiro-cli binary at {self.kiro_cli_path} is not executable."
            )

    def _build_command(self) -> list[str]:
        """Build the kiro-cli command with appropriate flags."""
        # Validate model against allowlist to prevent flag injection
        if self.model not in KIRO_MODELS:
            logger.warning("Unknown model '%s', falling back to claude-sonnet-4.6", self.model)
            model = "claude-sonnet-4.6"
        else:
            model = self.model

        cmd = [
            self.kiro_cli_path,
            "chat",
            "--no-interactive",
            "--model", model,
            "--trust-all-tools",
            "--wrap", "never",
        ]
        if self.agent_name:
            cmd.extend(["--agent", self.agent_name])
        return cmd

    def _messages_to_prompt(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-style messages to a prompt string for kiro-cli.

        Preserves system prompts, multi-turn context, and tool results.
        """
        parts = []

        # Extract system messages
        system_msgs = [m for m in messages if m.get("role") == "system"]
        other_msgs = [m for m in messages if m.get("role") != "system"]

        # System prompt goes first
        if system_msgs:
            system_content = system_msgs[-1].get("content", "")
            if isinstance(system_content, list):
                system_content = " ".join(
                    p.get("text", "") for p in system_content
                    if isinstance(p, dict) and p.get("type") == "text"
                )
            parts.append(f"[System Instructions]\n{system_content}\n[End System Instructions]")

        # Convert conversation turns
        for msg in other_msgs:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle list-type content (multimodal)
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("text", ""))
                        elif part.get("type") == "tool_result":
                            text_parts.append(f"[Tool Result: {part.get('content', '')}]")
                content = "\n".join(text_parts)

            # Handle tool calls in assistant messages
            tool_calls = msg.get("tool_calls", [])
            if tool_calls:
                tc_parts = []
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    tc_parts.append(
                        f"[Tool Call: {fn.get('name', '?')}({fn.get('arguments', '{}')})]"
                    )
                if content:
                    content = content + "\n" + "\n".join(tc_parts)
                else:
                    content = "\n".join(tc_parts)

            # Handle tool role messages
            if role == "tool":
                tool_name = msg.get("name", "unknown")
                parts.append(f"[Tool Result ({tool_name})]: {content}")
                continue

            label = {"user": "User", "assistant": "Assistant"}.get(role, role.title())
            if content:
                parts.append(f"{label}: {content}")

        # End with assistant prompt
        if other_msgs and other_msgs[-1].get("role") == "user":
            parts.append("\nAssistant:")

        return "\n\n".join(parts)

    def chat_completion(
        self,
        messages: List[Dict[str, Any]],
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any] | Generator[Dict[str, Any], None, None]:
        """Execute a chat completion via kiro-cli subprocess.

        Args:
            messages: OpenAI-style message list
            stream: If True, yield chunks as they arrive
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Complete response dict (non-streaming) or generator of chunks (streaming)
        """
        prompt = self._messages_to_prompt(messages)

        if stream:
            return self._stream_completion(prompt)
        else:
            return self._sync_completion(prompt)

    def _sync_completion(self, prompt: str) -> Dict[str, Any]:
        """Run kiro-cli synchronously and return the complete response."""
        try:
            result = subprocess.run(
                self._build_command(),
                input=prompt,
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            content = _clean_kiro_output(result.stdout)
            if not content:
                content = "I'm ready to help. What would you like to work on?"

        except subprocess.TimeoutExpired:
            content = f"[Response timed out after {self.timeout}s]"
            logger.warning("kiro-cli timed out after %ds", self.timeout)
        except Exception as e:
            content = f"[Error communicating with kiro-cli: {str(e)[:200]}]"
            logger.error("kiro-cli error: %s", e)

        return {
            "id": f"kiro-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": self.model,
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split()),
            },
        }

    def _stream_completion(self, prompt: str) -> Generator[Dict[str, Any], None, None]:
        """Run kiro-cli and stream output line by line."""
        import fcntl
        import sys

        created = int(time.time())
        completion_id = f"kiro-{created}"
        process = None

        try:
            process = subprocess.Popen(
                self._build_command(),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,  # Prevent stderr pipe deadlock
                text=False,
            )
            process.stdin.write(prompt.encode("utf-8"))
            process.stdin.close()

            # Set stdout to non-blocking (Unix only)
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
                        time.sleep(0.05)
                        continue
                except (BlockingIOError, IOError):
                    if retcode is not None:
                        break
                    time.sleep(0.05)
                    continue

                # Yield complete lines
                while "\n" in buffer:
                    nl = buffer.find("\n")
                    line = buffer[:nl]
                    buffer = buffer[nl + 1:]

                    line = _strip_ansi(line)
                    if line.startswith("> "):
                        line = line[2:]
                    if _is_metadata_line(line.strip()):
                        continue
                    if any(phrase in line for phrase in _NOISE_PHRASES):
                        continue

                    yield {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": self.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": line + "\n"},
                            "finish_reason": None,
                        }],
                    }

            # Final drain: read any remaining data after process exits
            try:
                remaining_raw = process.stdout.read()
                if remaining_raw:
                    buffer += remaining_raw.decode("utf-8", errors="replace")
            except (BlockingIOError, IOError):
                pass

            # Flush remaining buffer
            if buffer.strip():
                remaining = _strip_ansi(buffer)
                if remaining.startswith("> "):
                    remaining = remaining[2:]
                if remaining.strip() and not _is_metadata_line(remaining.strip()):
                    yield {
                        "id": completion_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": self.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": remaining},
                            "finish_reason": None,
                        }],
                    }

            # Final chunk with finish_reason
            yield {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": self.model,
                "choices": [{
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }],
            }

        except Exception as e:
            logger.error("kiro-cli streaming error: %s", e)
            yield {
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": self.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": f"[Streaming error: {str(e)[:100]}]"},
                    "finish_reason": "stop",
                }],
            }
        finally:
            # Always clean up the subprocess to prevent zombies
            if process is not None and process.poll() is None:
                process.kill()
                process.wait(timeout=5)


# ─── Registration ─────────────────────────────────────────────────────────────

def get_profile() -> KiroCliProfile:
    """Return the kiro-cli provider profile for registration."""
    return KiroCliProfile()


def is_available() -> bool:
    """Check if kiro-cli is available on this system."""
    path = os.environ.get("KIRO_CLI_PATH", KIRO_CLI_DEFAULT_PATH)
    return os.path.isfile(path) and os.access(path, os.X_OK)


def get_context_length(model: str) -> int:
    """Return the context window size for a kiro-cli model."""
    return KIRO_CONTEXT_LENGTHS.get(model, 200_000)


def get_max_output_tokens(model: str) -> int:
    """Return the max output tokens for a kiro-cli model."""
    return KIRO_MAX_OUTPUT.get(model, 16_000)
