"""Role-Based Subagent Profiles — Specialized delegation with scoped tools.

Inspired by CrewAI's role-based agents and Goose's extension scoping.
Each role has a specialized system prompt addon, restricted toolset,
and tuned iteration budget.

Usage:
    from agent.role_profiles import get_role_profile, AVAILABLE_ROLES

    profile = get_role_profile("researcher")
    # Use profile.system_prompt_addon, profile.toolset, profile.max_iterations
    # when spawning a subagent via delegate_task
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoleProfile:
    """Configuration for a specialized subagent role."""

    name: str
    description: str
    system_prompt_addon: str
    toolset: str  # Maps to toolsets.py toolset name
    max_iterations: int = 30
    allowed_tools: List[str] = field(default_factory=list)  # Empty = use toolset default
    denied_tools: List[str] = field(default_factory=list)
    temperature: Optional[float] = None  # None = use default

    @property
    def full_system_prompt(self) -> str:
        """Return the complete role-specific system prompt."""
        return (
            f"## Your Role: {self.name.title()}\n\n"
            f"{self.system_prompt_addon}\n\n"
            f"## Constraints\n"
            f"- Stay focused on your role. Do not exceed your scope.\n"
            f"- Maximum iterations: {self.max_iterations}\n"
            f"- If you cannot complete the task within your role, report back clearly.\n"
        )


# ─── Built-in Role Profiles ──────────────────────────────────────────────────

ROLE_PROFILES: Dict[str, RoleProfile] = {
    "researcher": RoleProfile(
        name="researcher",
        description="Information gathering specialist. Finds, reads, and summarizes information.",
        system_prompt_addon=(
            "You are a research specialist. Your job is to FIND and SUMMARIZE information.\n"
            "- Search files, documentation, and the web thoroughly\n"
            "- Read and analyze code to understand architecture\n"
            "- Summarize findings clearly with specific references\n"
            "- Do NOT modify any files. Do NOT write code.\n"
            "- Do NOT execute commands that change state\n"
            "- Report what you found, with file paths and line numbers"
        ),
        toolset="web",
        max_iterations=25,
        denied_tools=["write_file", "patch", "execute_bash", "run_shell"],
    ),

    "developer": RoleProfile(
        name="developer",
        description="Senior developer. Writes clean, tested, production-quality code.",
        system_prompt_addon=(
            "You are a senior software developer. Write clean, well-tested code.\n"
            "- Follow existing code style and conventions\n"
            "- Write meaningful comments for complex logic\n"
            "- Handle errors gracefully\n"
            "- Consider edge cases\n"
            "- If tests exist, run them after making changes\n"
            "- Commit atomic, focused changes"
        ),
        toolset="hermes-cli",
        max_iterations=45,
    ),

    "reviewer": RoleProfile(
        name="reviewer",
        description="Code reviewer. Finds bugs, suggests improvements. Read-only.",
        system_prompt_addon=(
            "You are a code reviewer. Your job is to REVIEW, not modify.\n"
            "- Read the code carefully and identify issues\n"
            "- Look for: bugs, security issues, performance problems, style violations\n"
            "- Suggest specific improvements with code examples\n"
            "- Rate severity: critical / high / medium / low\n"
            "- Do NOT modify any files. Report findings only.\n"
            "- Be constructive — explain WHY something is a problem"
        ),
        toolset="safe",
        max_iterations=20,
        denied_tools=["write_file", "patch", "execute_bash", "run_shell", "delegate_task"],
    ),

    "planner": RoleProfile(
        name="planner",
        description="Task decomposition specialist. Breaks complex work into actionable steps.",
        system_prompt_addon=(
            "You are a planning specialist. Break complex tasks into clear, actionable steps.\n"
            "- Analyze the task requirements thoroughly\n"
            "- Identify dependencies between subtasks\n"
            "- Estimate complexity for each step\n"
            "- Define clear acceptance criteria\n"
            "- Consider risks and fallback approaches\n"
            "- Output a structured plan (numbered steps with dependencies)\n"
            "- Do NOT implement anything. Plan only."
        ),
        toolset="safe",
        max_iterations=15,
        denied_tools=["write_file", "patch", "execute_bash"],
    ),

    "debugger": RoleProfile(
        name="debugger",
        description="Debugging specialist. Systematic root cause analysis.",
        system_prompt_addon=(
            "You are a debugging specialist. Find the ROOT CAUSE, not just symptoms.\n"
            "- Reproduce the issue first\n"
            "- Form hypotheses and test them systematically\n"
            "- Use binary search to narrow down the problem\n"
            "- Check logs, stack traces, and error messages carefully\n"
            "- Once found, explain the root cause clearly\n"
            "- Suggest a minimal fix (but don't implement unless asked)"
        ),
        toolset="hermes-cli",
        max_iterations=35,
    ),

    "tester": RoleProfile(
        name="tester",
        description="Testing specialist. Writes and runs tests, validates behavior.",
        system_prompt_addon=(
            "You are a testing specialist. Ensure code works correctly.\n"
            "- Write tests that cover: happy path, edge cases, error cases\n"
            "- Use the project's existing test framework\n"
            "- Run tests and report results\n"
            "- If tests fail, analyze why and report (don't fix the code)\n"
            "- Aim for meaningful coverage, not 100% line coverage\n"
            "- Test behavior, not implementation details"
        ),
        toolset="hermes-cli",
        max_iterations=30,
    ),

    "documenter": RoleProfile(
        name="documenter",
        description="Documentation specialist. Writes clear, accurate docs.",
        system_prompt_addon=(
            "You are a documentation specialist. Write clear, accurate documentation.\n"
            "- Read the code to understand what it does\n"
            "- Write for the target audience (developers, users, or both)\n"
            "- Include examples and usage patterns\n"
            "- Keep it concise — every sentence should add value\n"
            "- Use consistent formatting (markdown)\n"
            "- Document the WHY, not just the WHAT"
        ),
        toolset="hermes-cli",
        max_iterations=25,
        denied_tools=["execute_bash", "run_shell"],
    ),

    "refactorer": RoleProfile(
        name="refactorer",
        description="Refactoring specialist. Improves code structure without changing behavior.",
        system_prompt_addon=(
            "You are a refactoring specialist. Improve code structure.\n"
            "- Do NOT change behavior — only structure\n"
            "- Run tests before AND after refactoring\n"
            "- Make small, incremental changes\n"
            "- Improve: naming, modularity, duplication, complexity\n"
            "- If tests don't exist, write them first\n"
            "- Each change should be independently reviewable"
        ),
        toolset="hermes-cli",
        max_iterations=40,
    ),
}


# ─── Public API ───────────────────────────────────────────────────────────────

AVAILABLE_ROLES = list(ROLE_PROFILES.keys())


def get_role_profile(role: str) -> Optional[RoleProfile]:
    """Get a role profile by name. Returns None if not found."""
    if not role or not isinstance(role, str):
        return None
    return ROLE_PROFILES.get(role.lower().strip())


def list_roles() -> List[Dict[str, str]]:
    """Return a list of available roles with descriptions."""
    return [
        {"name": p.name, "description": p.description}
        for p in ROLE_PROFILES.values()
    ]


def register_role(profile: RoleProfile) -> None:
    """Register a custom role profile."""
    ROLE_PROFILES[profile.name.lower()] = profile
    if profile.name.lower() not in AVAILABLE_ROLES:
        AVAILABLE_ROLES.append(profile.name.lower())
    logger.info("Registered custom role: %s", profile.name)


def get_role_for_task(task_description: str) -> str:
    """Heuristic: suggest a role based on task description keywords.

    Returns the role name that best matches the task.
    """
    if not task_description or not isinstance(task_description, str):
        return "developer"
    task_lower = task_description.lower()

    # Keyword matching (simple heuristic)
    if any(w in task_lower for w in ["find", "search", "research", "look up", "what is", "summarize"]):
        return "researcher"
    if any(w in task_lower for w in ["review", "check", "audit", "inspect", "evaluate"]):
        return "reviewer"
    if any(w in task_lower for w in ["plan", "break down", "decompose", "design", "architect"]):
        return "planner"
    if any(w in task_lower for w in ["debug", "fix", "why", "broken", "error", "crash", "failing"]):
        return "debugger"
    if any(w in task_lower for w in ["test", "verify", "validate", "assert", "coverage"]):
        return "tester"
    if any(w in task_lower for w in ["document", "readme", "docs", "explain", "describe"]):
        return "documenter"
    if any(w in task_lower for w in ["refactor", "clean up", "restructure", "simplify", "extract"]):
        return "refactorer"

    # Default to developer for implementation tasks
    return "developer"
