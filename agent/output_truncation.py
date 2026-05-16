"""Enhanced Output Truncation — Informative truncation with guidance.

Inspired by SWE-agent's approach: when output is truncated, tell the agent
exactly what was cut and how to get the full content.

Instead of silently cutting output, provide:
- How many lines/chars were truncated
- What section was kept (head, tail, or both)
- Suggestions for how to get the full content

Usage:
    from agent.output_truncation import smart_truncate

    result = smart_truncate(long_output, max_chars=3000)
    # Returns truncated text with informative markers
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def smart_truncate(
    text: str,
    *,
    max_chars: int = 3000,
    max_lines: int = 100,
    strategy: str = "head_tail",
    context_hint: str = "",
) -> str:
    """Truncate text with informative markers.

    Args:
        text: The text to potentially truncate
        max_chars: Maximum characters to keep
        max_lines: Maximum lines to keep
        strategy: "head_tail" (keep both ends), "head" (keep start), "tail" (keep end)
        context_hint: Optional hint about what the content is (for guidance messages)

    Returns:
        Original text if within limits, or truncated text with markers
    """
    if not text:
        return text

    lines = text.split("\n")
    total_chars = len(text)
    total_lines = len(lines)

    # Check if truncation is needed
    needs_char_truncation = total_chars > max_chars
    needs_line_truncation = total_lines > max_lines

    if not needs_char_truncation and not needs_line_truncation:
        return text

    # Determine effective limit
    if needs_line_truncation and not needs_char_truncation:
        # Truncate by lines
        return _truncate_by_lines(lines, max_lines, total_lines, strategy, context_hint)
    elif needs_char_truncation:
        # Truncate by chars (more aggressive)
        return _truncate_by_chars(text, max_chars, total_chars, total_lines, strategy, context_hint)

    return text


def _truncate_by_lines(
    lines: list[str],
    max_lines: int,
    total_lines: int,
    strategy: str,
    context_hint: str,
) -> str:
    """Truncate by line count."""
    omitted = total_lines - max_lines
    hint = f" ({context_hint})" if context_hint else ""

    if strategy == "head":
        kept = lines[:max_lines]
        marker = (
            f"\n[... {omitted} more lines omitted{hint}. "
            f"Total: {total_lines} lines. Showing first {max_lines}.]"
        )
        return "\n".join(kept) + marker

    elif strategy == "tail":
        kept = lines[-max_lines:]
        marker = (
            f"[... {omitted} lines omitted from start{hint}. "
            f"Total: {total_lines} lines. Showing last {max_lines}.]\n"
        )
        return marker + "\n".join(kept)

    else:  # head_tail
        head_count = max_lines // 2
        tail_count = max_lines - head_count
        head = lines[:head_count]
        tail = lines[-tail_count:]
        marker = (
            f"\n[... {omitted} lines omitted{hint}. "
            f"Total: {total_lines} lines. "
            f"Showing first {head_count} + last {tail_count}. "
            f"Use grep or read_file with line range to see specific sections.]\n"
        )
        return "\n".join(head) + marker + "\n".join(tail)


def _truncate_by_chars(
    text: str,
    max_chars: int,
    total_chars: int,
    total_lines: int,
    strategy: str,
    context_hint: str,
) -> str:
    """Truncate by character count."""
    omitted = total_chars - max_chars
    hint = f" ({context_hint})" if context_hint else ""

    if strategy == "head":
        kept = text[:max_chars]
        marker = (
            f"\n[... {omitted:,} chars omitted{hint}. "
            f"Total: {total_chars:,} chars / {total_lines} lines. "
            f"Showing first {max_chars:,} chars.]"
        )
        return kept + marker

    elif strategy == "tail":
        kept = text[-max_chars:]
        marker = (
            f"[... {omitted:,} chars omitted from start{hint}. "
            f"Total: {total_chars:,} chars / {total_lines} lines. "
            f"Showing last {max_chars:,} chars.]\n"
        )
        return marker + kept

    else:  # head_tail
        head_chars = max_chars // 2
        tail_chars = max_chars - head_chars
        head = text[:head_chars]
        tail = text[-tail_chars:]
        marker = (
            f"\n[... {omitted:,} chars omitted{hint}. "
            f"Total: {total_chars:,} chars / {total_lines} lines. "
            f"Showing first {head_chars:,} + last {tail_chars:,} chars. "
            f"Use grep to find specific content, or read_file with line range.]\n"
        )
        return head + marker + tail


def truncate_tool_result(
    result: str,
    tool_name: str,
    *,
    max_chars: int = 5000,
    max_lines: int = 150,
) -> str:
    """Truncate a tool result with tool-specific guidance.

    Provides contextual hints based on which tool produced the output.
    """
    if not result or (len(result) <= max_chars and result.count("\n") <= max_lines):
        return result

    # Tool-specific hints
    hints = {
        "execute_bash": "Re-run with | head or | tail, or redirect to a file",
        "read_file": "Use start_line/end_line params to read specific sections",
        "grep": "Add more specific patterns or use --max-count to limit results",
        "search_files": "Narrow the search pattern or add file type filters",
        "list_dir": "Use a more specific path or add depth limit",
        "web_fetch": "Use selective mode with a search phrase",
        "web_search": "Reduce max_results or use a more specific query",
    }

    context_hint = hints.get(tool_name, "")

    return smart_truncate(
        result,
        max_chars=max_chars,
        max_lines=max_lines,
        strategy="head_tail",
        context_hint=context_hint,
    )
