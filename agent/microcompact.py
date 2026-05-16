"""Microcompact: LLM-free surgical context stripping.

Inspired by community issue #525 — strips tool call/result pairs and thinking
blocks WITHOUT LLM summarization. Instant, free, lossless for actual
conversational content.

Context is often 70-90% tool call/result pairs and thinking blocks. This module
provides a "scalpel" approach vs the "grenade" of full LLM-based compression.

Three-layer system:
  1. microcompact (silent, every turn) — this module
  2. auto-compact (threshold-based LLM summarization)
  3. /compact (manual full compression)

Usage:
    from agent.microcompact import microcompact_messages

    messages = microcompact_messages(
        messages,
        protect_last_n=5,       # Keep last N tool results intact ("hot tail")
        max_tool_result_chars=500,  # Truncate old tool results to this length
        strip_thinking=True,    # Remove <think>...</think> blocks
    )
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Regex for thinking/reasoning blocks
_THINK_BLOCK_RE = re.compile(
    r"<think>.*?</think>",
    re.DOTALL | re.IGNORECASE,
)
_REASONING_BLOCK_RE = re.compile(
    r"<reasoning>.*?</reasoning>",
    re.DOTALL | re.IGNORECASE,
)


def _content_char_count(content: Any) -> int:
    """Count characters in message content (handles str and list formats)."""
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text":
                    total += len(part.get("text", ""))
                elif part.get("type") == "tool_result":
                    total += len(str(part.get("content", "")))
        return total
    return 0


def _truncate_content(content: Any, max_chars: int) -> Any:
    """Truncate content to max_chars, preserving structure."""
    if isinstance(content, str):
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + f"\n[... truncated {len(content) - max_chars} chars]"

    if isinstance(content, list):
        result = []
        remaining = max_chars
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                if len(text) <= remaining:
                    result.append(part)
                    remaining -= len(text)
                else:
                    result.append({
                        "type": "text",
                        "text": text[:remaining] + f"\n[... truncated {len(text) - remaining} chars]",
                    })
                    remaining = 0
            else:
                result.append(part)
        return result

    return content


def _strip_thinking_from_content(content: Any) -> Any:
    """Remove <think>...</think> and <reasoning>...</reasoning> blocks."""
    if isinstance(content, str):
        content = _THINK_BLOCK_RE.sub("", content)
        content = _REASONING_BLOCK_RE.sub("", content)
        return content.strip()

    if isinstance(content, list):
        result = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                text = part.get("text", "")
                text = _THINK_BLOCK_RE.sub("", text)
                text = _REASONING_BLOCK_RE.sub("", text)
                text = text.strip()
                if text:
                    result.append({"type": "text", "text": text})
            else:
                result.append(part)
        return result if result else ""

    return content


def microcompact_messages(
    messages: List[Dict[str, Any]],
    *,
    protect_last_n: int = 5,
    max_tool_result_chars: int = 500,
    strip_thinking: bool = True,
    strip_empty_tool_results: bool = True,
    collapse_consecutive_tool_pairs: bool = True,
) -> List[Dict[str, Any]]:
    """Apply surgical, LLM-free context stripping to messages.

    This is designed to be called BEFORE each API call to minimize context
    usage without losing conversational content.

    Args:
        messages: The full message history
        protect_last_n: Number of recent messages to leave untouched
        max_tool_result_chars: Max chars for old tool results (0 = remove entirely)
        strip_thinking: Remove <think>...</think> blocks from assistant messages
        strip_empty_tool_results: Remove tool results that are empty or just "ok"
        collapse_consecutive_tool_pairs: Collapse multiple tool call/result pairs
            into a summary when they're far from the conversation tail

    Returns:
        Compacted message list (new list, original not mutated)
    """
    if not messages:
        return messages

    # Separate system message (always preserved)
    system_msgs = [m for m in messages if m.get("role") == "system"]
    non_system = [m for m in messages if m.get("role") != "system"]

    if not non_system:
        return messages

    # Split into protected tail and compactable head
    if protect_last_n >= len(non_system):
        head = []
        tail = non_system
    else:
        head = non_system[:-protect_last_n] if protect_last_n > 0 else non_system
        tail = non_system[-protect_last_n:] if protect_last_n > 0 else []

    # Process head messages (aggressive compaction)
    compacted_head = []
    chars_saved = 0
    messages_removed = 0

    i = 0
    while i < len(head):
        msg = head[i]
        role = msg.get("role", "")
        content = msg.get("content", "")

        # Strip thinking blocks from assistant messages
        if strip_thinking and role == "assistant" and content:
            original_len = _content_char_count(content)
            new_content = _strip_thinking_from_content(content)
            new_len = _content_char_count(new_content)
            if new_len < original_len:
                chars_saved += original_len - new_len
                msg = {**msg, "content": new_content}

        # Handle tool results
        if role == "tool":
            content_len = _content_char_count(content)

            # Strip empty/trivial tool results
            if strip_empty_tool_results:
                content_str = content if isinstance(content, str) else str(content)
                if content_str.strip().lower() in ("", "ok", "done", "success", "null", "none"):
                    messages_removed += 1
                    chars_saved += content_len
                    i += 1
                    continue

            # Truncate large tool results
            if content_len > max_tool_result_chars and max_tool_result_chars > 0:
                chars_saved += content_len - max_tool_result_chars
                msg = {**msg, "content": _truncate_content(content, max_tool_result_chars)}
            elif max_tool_result_chars == 0:
                # Remove entirely, replace with brief note
                tool_name = msg.get("name", "tool")
                chars_saved += content_len
                msg = {**msg, "content": f"[{tool_name} result omitted for brevity]"}

        # Handle assistant messages with tool_calls (truncate arguments)
        if role == "assistant" and msg.get("tool_calls"):
            tool_calls = msg["tool_calls"]
            compacted_calls = []
            for tc in tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", "{}")
                if len(args) > 200:
                    chars_saved += len(args) - 200
                    fn = {**fn, "arguments": args[:200] + "..."}
                    tc = {**tc, "function": fn}
                compacted_calls.append(tc)
            msg = {**msg, "tool_calls": compacted_calls}

        compacted_head.append(msg)
        i += 1

    # Process tail messages (light touch — only strip thinking)
    compacted_tail = []
    for msg in tail:
        if strip_thinking and msg.get("role") == "assistant":
            content = msg.get("content", "")
            if content:
                new_content = _strip_thinking_from_content(content)
                if _content_char_count(new_content) < _content_char_count(content):
                    chars_saved += _content_char_count(content) - _content_char_count(new_content)
                    msg = {**msg, "content": new_content}
        compacted_tail.append(msg)

    result = system_msgs + compacted_head + compacted_tail

    if chars_saved > 0 or messages_removed > 0:
        logger.info(
            "Microcompact: saved ~%d chars, removed %d messages",
            chars_saved, messages_removed,
        )

    return result


def estimate_savings(messages: List[Dict[str, Any]], protect_last_n: int = 5) -> Dict[str, int]:
    """Estimate how much microcompact would save without actually doing it.

    Returns:
        Dict with 'thinking_chars', 'tool_result_chars', 'total_chars', 'removable_messages'
    """
    non_system = [m for m in messages if m.get("role") != "system"]
    if protect_last_n >= len(non_system):
        return {"thinking_chars": 0, "tool_result_chars": 0, "total_chars": 0, "removable_messages": 0}

    head = non_system[:-protect_last_n] if protect_last_n > 0 else non_system

    thinking_chars = 0
    tool_result_chars = 0
    removable_messages = 0

    for msg in head:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "assistant" and content:
            content_str = content if isinstance(content, str) else str(content)
            for match in _THINK_BLOCK_RE.finditer(content_str):
                thinking_chars += len(match.group())
            for match in _REASONING_BLOCK_RE.finditer(content_str):
                thinking_chars += len(match.group())

        if role == "tool":
            content_len = _content_char_count(content)
            if content_len > 500:
                tool_result_chars += content_len - 500
            content_str = content if isinstance(content, str) else str(content)
            if content_str.strip().lower() in ("", "ok", "done", "success", "null", "none"):
                removable_messages += 1

    return {
        "thinking_chars": thinking_chars,
        "tool_result_chars": tool_result_chars,
        "total_chars": thinking_chars + tool_result_chars,
        "removable_messages": removable_messages,
    }
