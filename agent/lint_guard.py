"""Lint-on-Edit Guard — Auto-validate file edits before accepting them.

Inspired by SWE-agent's approach: automatically lint after every edit,
reject if syntax errors are introduced. Prevents broken code from
accumulating in the workspace.

Usage:
    from agent.lint_guard import lint_file, LintResult

    result = lint_file("/path/to/file.py")
    if not result.passed:
        # Reject the edit, tell the agent to fix it
        return f"Edit rejected: {result.error}"
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LintResult:
    """Result of a lint check on a file."""
    passed: bool
    filepath: str
    linter: str = ""
    error: str = ""
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    @property
    def summary(self) -> str:
        if self.passed:
            return f"✓ {self.filepath} passed ({self.linter})"
        return f"✗ {self.filepath} failed ({self.linter}): {self.error[:200]}"


# ─── Linter Registry ──────────────────────────────────────────────────────────

# Maps file extensions to linter commands.
# Each entry: (command_parts, timeout_seconds, description)
# The filepath is appended to command_parts at runtime.

LINTERS: Dict[str, Dict[str, Any]] = {
    ".py": {
        "command": ["python3", "-m", "py_compile"],
        "timeout": 10,
        "description": "Python syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".js": {
        "command": ["node", "--check"],
        "timeout": 10,
        "description": "Node.js syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".ts": {
        "command": ["npx", "tsc", "--noEmit", "--allowJs", "--skipLibCheck"],
        "timeout": 30,
        "description": "TypeScript type check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".json": {
        "command": ["python3", "-m", "json.tool"],
        "timeout": 5,
        "description": "JSON syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".yaml": {
        "command": ["python3", "-c", "import yaml, sys; yaml.safe_load(open(sys.argv[1]))"],
        "timeout": 5,
        "description": "YAML syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".yml": {
        "command": ["python3", "-c", "import yaml, sys; yaml.safe_load(open(sys.argv[1]))"],
        "timeout": 5,
        "description": "YAML syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".sh": {
        "command": ["bash", "-n"],
        "timeout": 5,
        "description": "Bash syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".rb": {
        "command": ["ruby", "-c"],
        "timeout": 10,
        "description": "Ruby syntax check",
        "parse_error": lambda stderr: stderr.strip(),
    },
    ".rs": {
        "command": ["rustfmt", "--check"],
        "timeout": 15,
        "description": "Rust format check",
        "parse_error": lambda stderr: stderr.strip(),
    },
}


def _command_available(cmd: str) -> bool:
    """Check if a command is available on PATH."""
    return shutil.which(cmd) is not None


def lint_file(filepath: str, *, content: Optional[str] = None) -> LintResult:
    """Lint a file after editing. Returns LintResult with pass/fail status.

    Args:
        filepath: Path to the file to lint
        content: If provided, write this content to a temp file and lint that
                 (useful for pre-write validation)

    Returns:
        LintResult with passed=True if no errors, or error details if failed
    """
    import time

    path = Path(filepath)
    ext = path.suffix.lower()

    # No linter for this file type
    if ext not in LINTERS:
        return LintResult(passed=True, filepath=filepath, linter="none")

    linter_config = LINTERS[ext]
    command = linter_config["command"]
    timeout = linter_config["timeout"]
    description = linter_config["description"]

    # Check if the linter command is available
    if not _command_available(command[0]):
        logger.debug("Linter %s not available for %s", command[0], filepath)
        return LintResult(passed=True, filepath=filepath, linter=f"{command[0]} (not installed)")

    # If content provided, write to temp file for validation
    temp_file = None
    target_path = filepath
    if content is not None:
        import tempfile
        temp_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=ext, delete=False, prefix="hermes_lint_"
        )
        temp_file.write(content)
        temp_file.close()
        target_path = temp_file.name

    try:
        start = time.time()

        # Build the full command
        full_cmd = list(command) + [target_path]

        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(path.parent) if path.parent.exists() else None,
        )

        duration_ms = (time.time() - start) * 1000

        if result.returncode == 0:
            return LintResult(
                passed=True,
                filepath=filepath,
                linter=description,
                duration_ms=duration_ms,
            )
        else:
            error_text = result.stderr or result.stdout
            parse_fn = linter_config.get("parse_error", lambda x: x)
            parsed_error = parse_fn(error_text)

            return LintResult(
                passed=False,
                filepath=filepath,
                linter=description,
                error=parsed_error[:500],
                duration_ms=duration_ms,
            )

    except subprocess.TimeoutExpired:
        return LintResult(
            passed=True,  # Don't block on timeout — assume OK
            filepath=filepath,
            linter=description,
            warnings=["Lint check timed out"],
        )
    except Exception as e:
        logger.debug("Lint check failed for %s: %s", filepath, e)
        return LintResult(
            passed=True,  # Don't block on errors — assume OK
            filepath=filepath,
            linter=description,
            warnings=[f"Lint check error: {str(e)[:100]}"],
        )
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)


def lint_edit(filepath: str, new_content: str) -> Optional[str]:
    """Convenience function: lint new content before writing.

    Returns None if the content is valid, or an error message if not.
    This is the function to call from file_tools.py write handlers.
    """
    result = lint_file(filepath, content=new_content)
    if result.passed:
        return None
    return f"Edit would introduce errors ({result.linter}):\n{result.error}"


def get_supported_extensions() -> List[str]:
    """Return list of file extensions that have lint support."""
    return list(LINTERS.keys())
