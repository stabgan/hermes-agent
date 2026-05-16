"""Structured Memory Blocks — Always-in-context labeled memory sections.

Inspired by Letta/MemGPT's tiered memory architecture. Memory is organized
into labeled blocks that are ALWAYS present in the system prompt, giving the
agent persistent awareness of its identity, the user, and current context.

Blocks:
  - persona: Agent identity and capabilities (from SOUL.md)
  - human: Key details about the user (from USER.md)
  - project: Current project context, tech stack, conventions
  - scratchpad: Working memory for current task state (survives compression)

The agent can read and write these blocks via tool calls, and they're
injected into the system prompt on every turn.

Usage:
    from agent.memory_blocks import MemoryBlockStore

    store = MemoryBlockStore()
    store.load_from_disk()

    # Get formatted blocks for system prompt injection
    prompt_section = store.format_for_prompt()

    # Agent updates a block
    store.update_block("human", "Prefers TypeScript. Works at Google.")
    store.save_to_disk()
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MemoryBlock:
    """A single labeled memory block."""

    label: str
    description: str
    content: str = ""
    max_chars: int = 2000
    always_in_context: bool = True
    last_modified: float = 0.0

    @property
    def char_count(self) -> int:
        return len(self.content)

    @property
    def usage_pct(self) -> float:
        if self.max_chars == 0:
            return 0.0
        return (self.char_count / self.max_chars) * 100

    def update(self, new_content: str) -> bool:
        """Update block content. Returns False if exceeds max_chars."""
        if len(new_content) > self.max_chars:
            return False
        self.content = new_content
        self.last_modified = time.time()
        return True

    def append(self, text: str) -> bool:
        """Append text to block. Returns False if would exceed max_chars."""
        new_content = self.content + "\n" + text if self.content else text
        if len(new_content) > self.max_chars:
            return False
        self.content = new_content
        self.last_modified = time.time()
        return True

    def replace(self, old_text: str, new_text: str) -> bool:
        """Replace text within block. Returns False if not found or exceeds limit."""
        if old_text not in self.content:
            return False
        new_content = self.content.replace(old_text, new_text, 1)
        if len(new_content) > self.max_chars:
            return False
        self.content = new_content
        self.last_modified = time.time()
        return True


# ─── Default Block Definitions ────────────────────────────────────────────────

DEFAULT_BLOCKS = {
    "persona": MemoryBlock(
        label="persona",
        description="Your identity, capabilities, and behavioral guidelines",
        max_chars=2500,
        always_in_context=True,
    ),
    "human": MemoryBlock(
        label="human",
        description="Key details about the user you're conversing with",
        max_chars=2000,
        always_in_context=True,
    ),
    "project": MemoryBlock(
        label="project",
        description="Current project context, tech stack, conventions, and key decisions",
        max_chars=3000,
        always_in_context=True,
    ),
    "scratchpad": MemoryBlock(
        label="scratchpad",
        description="Working memory for current task state. Survives context compression.",
        max_chars=1500,
        always_in_context=True,
    ),
}


class MemoryBlockStore:
    """Manages structured memory blocks with persistence."""

    def __init__(self, hermes_home: Optional[str] = None):
        if hermes_home:
            self._home = Path(hermes_home)
        else:
            self._home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        self._blocks_dir = self._home / "memory_blocks"
        self.blocks: Dict[str, MemoryBlock] = {}
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Set up default block definitions."""
        for label, block in DEFAULT_BLOCKS.items():
            self.blocks[label] = MemoryBlock(
                label=block.label,
                description=block.description,
                content=block.content,
                max_chars=block.max_chars,
                always_in_context=block.always_in_context,
            )

    def load_from_disk(self) -> None:
        """Load block contents from disk."""
        self._blocks_dir.mkdir(parents=True, exist_ok=True)

        for label in self.blocks:
            filepath = self._blocks_dir / f"{label}.md"
            if filepath.exists():
                try:
                    content = filepath.read_text(encoding="utf-8").strip()
                    self.blocks[label].content = content[:self.blocks[label].max_chars]
                    self.blocks[label].last_modified = filepath.stat().st_mtime
                except Exception as e:
                    logger.warning("Failed to load memory block %s: %s", label, e)

        # Also load from legacy files (SOUL.md → persona, USER.md → human)
        self._load_legacy_files()

    def _load_legacy_files(self) -> None:
        """Load from legacy MEMORY.md/USER.md/SOUL.md if blocks are empty."""
        # SOUL.md → persona block
        soul_path = self._home / "SOUL.md"
        if soul_path.exists() and not self.blocks["persona"].content:
            try:
                content = soul_path.read_text(encoding="utf-8").strip()
                self.blocks["persona"].content = content[:self.blocks["persona"].max_chars]
            except Exception:
                pass

        # USER.md → human block
        user_path = self._home / "USER.md"
        if user_path.exists() and not self.blocks["human"].content:
            try:
                content = user_path.read_text(encoding="utf-8").strip()
                self.blocks["human"].content = content[:self.blocks["human"].max_chars]
            except Exception:
                pass

        # MEMORY.md → project block (partial)
        memory_path = self._home / "MEMORY.md"
        if memory_path.exists() and not self.blocks["project"].content:
            try:
                content = memory_path.read_text(encoding="utf-8").strip()
                self.blocks["project"].content = content[:self.blocks["project"].max_chars]
            except Exception:
                pass

    def save_to_disk(self) -> None:
        """Persist all blocks to disk."""
        self._blocks_dir.mkdir(parents=True, exist_ok=True)

        for label, block in self.blocks.items():
            filepath = self._blocks_dir / f"{label}.md"
            try:
                filepath.write_text(block.content, encoding="utf-8")
            except Exception as e:
                logger.warning("Failed to save memory block %s: %s", label, e)

    def get_block(self, label: str) -> Optional[MemoryBlock]:
        """Get a block by label."""
        return self.blocks.get(label)

    def update_block(self, label: str, content: str) -> Dict[str, Any]:
        """Update a block's content. Returns status dict."""
        block = self.blocks.get(label)
        if not block:
            return {"success": False, "error": f"Block '{label}' not found. Available: {list(self.blocks.keys())}"}

        if len(content) > block.max_chars:
            return {
                "success": False,
                "error": f"Content too long ({len(content)} chars). Max for '{label}': {block.max_chars} chars.",
            }

        block.update(content)
        self.save_to_disk()
        return {"success": True, "block": label, "chars": len(content), "max": block.max_chars}

    def append_to_block(self, label: str, text: str) -> Dict[str, Any]:
        """Append text to a block. Returns status dict."""
        block = self.blocks.get(label)
        if not block:
            return {"success": False, "error": f"Block '{label}' not found."}

        if not block.append(text):
            return {
                "success": False,
                "error": f"Would exceed max chars ({block.max_chars}). Current: {block.char_count}. Trying to add: {len(text)}.",
            }

        self.save_to_disk()
        return {"success": True, "block": label, "chars": block.char_count, "max": block.max_chars}

    def replace_in_block(self, label: str, old_text: str, new_text: str) -> Dict[str, Any]:
        """Replace text within a block. Returns status dict."""
        block = self.blocks.get(label)
        if not block:
            return {"success": False, "error": f"Block '{label}' not found."}

        if not block.replace(old_text, new_text):
            if old_text not in block.content:
                return {"success": False, "error": f"Text not found in block '{label}'."}
            return {"success": False, "error": f"Replacement would exceed max chars ({block.max_chars})."}

        self.save_to_disk()
        return {"success": True, "block": label, "chars": block.char_count}

    def format_for_prompt(self) -> str:
        """Format all always-in-context blocks for system prompt injection.

        Returns a formatted string ready to be included in the system prompt.
        """
        sections = []

        for label, block in self.blocks.items():
            if not block.always_in_context:
                continue
            if not block.content:
                continue

            sections.append(
                f"<memory_block label=\"{label}\" "
                f"chars=\"{block.char_count}/{block.max_chars}\">\n"
                f"{block.content}\n"
                f"</memory_block>"
            )

        if not sections:
            return ""

        return (
            "## Memory Blocks (always in context — you can update these)\n\n"
            + "\n\n".join(sections)
        )

    def get_status(self) -> List[Dict[str, Any]]:
        """Return status of all blocks."""
        return [
            {
                "label": b.label,
                "description": b.description,
                "chars": b.char_count,
                "max_chars": b.max_chars,
                "usage_pct": round(b.usage_pct, 1),
                "in_context": b.always_in_context,
            }
            for b in self.blocks.values()
        ]

    def clear_scratchpad(self) -> None:
        """Clear the scratchpad block (called at session end or goal completion)."""
        if "scratchpad" in self.blocks:
            self.blocks["scratchpad"].content = ""
            self.save_to_disk()
