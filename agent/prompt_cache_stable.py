"""Cache-stable prompt ordering for local models.

Addresses issue #4319 — KV cache invalidation on compression. Every context
compression cycle previously invalidated the KV cache by rebuilding the system
prompt, forcing the model to reprocess full context from scratch (multi-minute
pauses on large models).

Solution: Order the system prompt so STABLE sections come first and VOLATILE
sections come last. This preserves the KV cache prefix across compressions.

Prompt structure (cache-stable ordering):
    [STABLE] Agent identity (SOUL.md)
    [STABLE] Skills guidance
    [STABLE] Context files (AGENTS.md, .hermes.md)
    [STABLE] Tool definitions (implicit — handled by API)
    [VOLATILE] Memory snapshot (MEMORY.md, USER.md)
    [VOLATILE] Compression summary note
    [VOLATILE] Date/time

The key insight: everything before the first volatile section can be cached
across turns. For local models using kiro-cli, this means the KV cache for
the system prompt prefix is preserved even after compression.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CacheStablePromptBuilder:
    """Builds system prompts with cache-stable ordering.

    Separates prompt components into stable (rarely changing) and volatile
    (changing every turn) sections. The stable prefix is hashed to detect
    when the cache would be invalidated.
    """

    def __init__(self):
        self._stable_sections: List[str] = []
        self._volatile_sections: List[str] = []
        self._last_stable_hash: Optional[str] = None

    def add_stable(self, section: str, label: str = "") -> None:
        """Add a stable section (identity, skills, context files).

        These sections rarely change and form the cacheable prefix.
        """
        if not isinstance(section, str) or not section.strip():
            return
        if label:
            self._stable_sections.append(f"<!-- {label} -->\n{section.strip()}")
        else:
            self._stable_sections.append(section.strip())

    def add_volatile(self, section: str, label: str = "") -> None:
        """Add a volatile section (memory, timestamps, compression notes).

        These sections change frequently and go at the end.
        """
        if not isinstance(section, str) or not section.strip():
            return
        if label:
            self._volatile_sections.append(f"<!-- {label} -->\n{section.strip()}")
        else:
            self._volatile_sections.append(section.strip())

    def build(self) -> str:
        """Build the complete system prompt with stable-first ordering."""
        parts = []

        # Stable sections first (cacheable prefix)
        if self._stable_sections:
            parts.extend(self._stable_sections)

        # Volatile sections last (invalidates only the tail)
        if self._volatile_sections:
            parts.extend(self._volatile_sections)

        return "\n\n".join(parts)

    def get_stable_hash(self) -> str:
        """Get a hash of the stable sections for cache invalidation detection."""
        stable_content = "\n\n".join(self._stable_sections)
        return hashlib.sha256(stable_content.encode()).hexdigest()[:12]

    def would_invalidate_cache(self) -> bool:
        """Check if the stable sections have changed since last build.

        Returns True if the KV cache would be invalidated (stable prefix changed).
        """
        current_hash = self.get_stable_hash()
        if self._last_stable_hash is None:
            self._last_stable_hash = current_hash
            return False

        invalidated = current_hash != self._last_stable_hash
        if invalidated:
            logger.warning(
                "Cache-stable prefix changed: %s → %s (KV cache will be invalidated)",
                self._last_stable_hash, current_hash,
            )
        self._last_stable_hash = current_hash
        return invalidated

    def reset(self) -> None:
        """Clear all sections for a fresh build."""
        self._stable_sections.clear()
        self._volatile_sections.clear()
        self._last_stable_hash = None

    @property
    def stable_char_count(self) -> int:
        """Character count of the stable (cacheable) prefix."""
        return sum(len(s) for s in self._stable_sections)

    @property
    def volatile_char_count(self) -> int:
        """Character count of the volatile (non-cacheable) suffix."""
        return sum(len(s) for s in self._volatile_sections)

    @property
    def cache_ratio(self) -> float:
        """Ratio of stable (cacheable) content to total prompt size."""
        total = self.stable_char_count + self.volatile_char_count
        if total == 0:
            return 0.0
        return self.stable_char_count / total


def reorder_system_prompt_for_cache_stability(
    identity: str = "",
    skills_guidance: str = "",
    context_files: str = "",
    tool_guidance: str = "",
    memory_snapshot: str = "",
    compression_note: str = "",
    datetime_info: str = "",
    platform_hints: str = "",
    extra_stable: str = "",
    extra_volatile: str = "",
) -> str:
    """Convenience function to build a cache-stable system prompt.

    Args:
        identity: SOUL.md content (stable)
        skills_guidance: Skills index and guidance (stable)
        context_files: AGENTS.md, .hermes.md content (stable)
        tool_guidance: Tool usage instructions (stable)
        memory_snapshot: MEMORY.md + USER.md content (volatile)
        compression_note: Context compression summary (volatile)
        datetime_info: Current date/time (volatile)
        platform_hints: Platform-specific formatting (stable)
        extra_stable: Additional stable content
        extra_volatile: Additional volatile content

    Returns:
        Complete system prompt with cache-stable ordering
    """
    builder = CacheStablePromptBuilder()

    # Stable sections (cacheable prefix)
    builder.add_stable(identity, "identity")
    builder.add_stable(platform_hints, "platform")
    builder.add_stable(skills_guidance, "skills")
    builder.add_stable(context_files, "context")
    builder.add_stable(tool_guidance, "tools")
    builder.add_stable(extra_stable)

    # Volatile sections (non-cacheable suffix)
    builder.add_volatile(memory_snapshot, "memory")
    builder.add_volatile(compression_note, "compression")
    builder.add_volatile(datetime_info, "datetime")
    builder.add_volatile(extra_volatile)

    return builder.build()
