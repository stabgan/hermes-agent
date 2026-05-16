"""Tests for the kiro-cli integration features.

Tests:
- Lint-on-Edit Guard
- Role-Based Subagent Profiles
- Structured Memory Blocks
- Enhanced Output Truncation
- Microcompact (LLM-free context stripping)
- Cache-Stable Prompt Ordering
"""

import json
import os
import tempfile
import time
from pathlib import Path

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Lint-on-Edit Guard Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestLintGuard:
    """Tests for agent/lint_guard.py"""

    def test_valid_python_passes(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("x = 1\nprint(x)\n")
            f.flush()
            result = lint_file(f.name)
            assert result.passed is True
            os.unlink(f.name)

    def test_invalid_python_fails(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def foo(\n  # missing closing paren\n")
            f.flush()
            result = lint_file(f.name)
            assert result.passed is False
            assert result.error  # Should have error message
            os.unlink(f.name)

    def test_valid_json_passes(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value", "num": 42}')
            f.flush()
            result = lint_file(f.name)
            assert result.passed is True
            os.unlink(f.name)

    def test_invalid_json_fails(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value",}')  # trailing comma
            f.flush()
            result = lint_file(f.name)
            assert result.passed is False
            os.unlink(f.name)

    def test_valid_bash_passes(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\necho hello\n")
            f.flush()
            result = lint_file(f.name)
            assert result.passed is True
            os.unlink(f.name)

    def test_invalid_bash_fails(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
            f.write("#!/bin/bash\nif [ true; then\n")  # missing ]
            f.flush()
            result = lint_file(f.name)
            assert result.passed is False
            os.unlink(f.name)

    def test_unknown_extension_passes(self):
        from agent.lint_guard import lint_file

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("anything goes here")
            f.flush()
            result = lint_file(f.name)
            assert result.passed is True
            assert result.linter == "none"
            os.unlink(f.name)

    def test_lint_edit_convenience(self):
        from agent.lint_guard import lint_edit

        # Valid content
        error = lint_edit("/tmp/test.py", "x = 1\nprint(x)\n")
        assert error is None

        # Invalid content
        error = lint_edit("/tmp/test.py", "def foo(\n")
        assert error is not None
        assert "errors" in error.lower() or "syntax" in error.lower() or "invalid" in error.lower()

    def test_supported_extensions(self):
        from agent.lint_guard import get_supported_extensions

        exts = get_supported_extensions()
        assert ".py" in exts
        assert ".json" in exts
        assert ".sh" in exts


# ═══════════════════════════════════════════════════════════════════════════════
# Role-Based Subagent Profiles Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestRoleProfiles:
    """Tests for agent/role_profiles.py"""

    def test_all_roles_exist(self):
        from agent.role_profiles import AVAILABLE_ROLES, get_role_profile

        expected = ["researcher", "developer", "reviewer", "planner", "debugger", "tester", "documenter", "refactorer"]
        for role in expected:
            assert role in AVAILABLE_ROLES
            profile = get_role_profile(role)
            assert profile is not None
            assert profile.name == role

    def test_role_profile_has_required_fields(self):
        from agent.role_profiles import get_role_profile

        profile = get_role_profile("developer")
        assert profile.name == "developer"
        assert profile.description
        assert profile.system_prompt_addon
        assert profile.toolset
        assert profile.max_iterations > 0

    def test_researcher_has_denied_tools(self):
        from agent.role_profiles import get_role_profile

        profile = get_role_profile("researcher")
        assert "write_file" in profile.denied_tools
        assert "execute_bash" in profile.denied_tools

    def test_reviewer_is_read_only(self):
        from agent.role_profiles import get_role_profile

        profile = get_role_profile("reviewer")
        assert "write_file" in profile.denied_tools
        assert "patch" in profile.denied_tools
        assert profile.toolset == "safe"

    def test_developer_has_full_access(self):
        from agent.role_profiles import get_role_profile

        profile = get_role_profile("developer")
        assert profile.toolset == "hermes-cli"
        assert len(profile.denied_tools) == 0

    def test_get_role_for_task(self):
        from agent.role_profiles import get_role_for_task

        assert get_role_for_task("Find all files related to authentication") == "researcher"
        assert get_role_for_task("Review the PR for security issues") == "reviewer"
        assert get_role_for_task("Plan the migration to PostgreSQL") == "planner"
        assert get_role_for_task("Debug why the tests are failing") == "debugger"
        assert get_role_for_task("Write unit tests for the auth module") == "tester"
        assert get_role_for_task("Implement the user registration endpoint") == "developer"
        assert get_role_for_task("Refactor the database layer") == "refactorer"

    def test_full_system_prompt(self):
        from agent.role_profiles import get_role_profile

        profile = get_role_profile("researcher")
        prompt = profile.full_system_prompt
        assert "Your Role: Researcher" in prompt
        assert "Constraints" in prompt
        assert str(profile.max_iterations) in prompt

    def test_register_custom_role(self):
        from agent.role_profiles import RoleProfile, register_role, get_role_profile, AVAILABLE_ROLES

        custom = RoleProfile(
            name="security-auditor",
            description="Security specialist",
            system_prompt_addon="You audit code for security vulnerabilities.",
            toolset="safe",
            max_iterations=20,
        )
        register_role(custom)
        assert "security-auditor" in AVAILABLE_ROLES
        assert get_role_profile("security-auditor") is not None

    def test_list_roles(self):
        from agent.role_profiles import list_roles

        roles = list_roles()
        assert len(roles) >= 8
        assert all("name" in r and "description" in r for r in roles)


# ═══════════════════════════════════════════════════════════════════════════════
# Structured Memory Blocks Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestMemoryBlocks:
    """Tests for agent/memory_blocks.py"""

    def test_initialize_defaults(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            assert "persona" in store.blocks
            assert "human" in store.blocks
            assert "project" in store.blocks
            assert "scratchpad" in store.blocks

    def test_update_block(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            result = store.update_block("human", "User prefers Python. Works on AI projects.")
            assert result["success"] is True
            assert store.blocks["human"].content == "User prefers Python. Works on AI projects."

    def test_update_block_exceeds_limit(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            long_content = "x" * 10000  # Exceeds any block's max
            result = store.update_block("human", long_content)
            assert result["success"] is False
            assert "too long" in result["error"].lower() or "max" in result["error"].lower()

    def test_append_to_block(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            store.update_block("scratchpad", "Step 1: Done")
            result = store.append_to_block("scratchpad", "Step 2: In progress")
            assert result["success"] is True
            assert "Step 1: Done" in store.blocks["scratchpad"].content
            assert "Step 2: In progress" in store.blocks["scratchpad"].content

    def test_replace_in_block(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            store.update_block("project", "Tech stack: Python, FastAPI")
            result = store.replace_in_block("project", "FastAPI", "Django")
            assert result["success"] is True
            assert "Django" in store.blocks["project"].content
            assert "FastAPI" not in store.blocks["project"].content

    def test_persistence(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write
            store1 = MemoryBlockStore(hermes_home=tmpdir)
            store1.update_block("human", "Test persistence")
            store1.save_to_disk()

            # Read back
            store2 = MemoryBlockStore(hermes_home=tmpdir)
            store2.load_from_disk()
            assert store2.blocks["human"].content == "Test persistence"

    def test_format_for_prompt(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            store.update_block("persona", "I am Hermes")
            store.update_block("human", "User is a developer")

            prompt = store.format_for_prompt()
            assert "memory_block" in prompt
            assert "persona" in prompt
            assert "I am Hermes" in prompt
            assert "User is a developer" in prompt

    def test_empty_blocks_not_in_prompt(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            # All blocks empty
            prompt = store.format_for_prompt()
            assert prompt == ""  # Nothing to show

    def test_clear_scratchpad(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            store.update_block("scratchpad", "Current task: building API")
            store.clear_scratchpad()
            assert store.blocks["scratchpad"].content == ""

    def test_get_status(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            store.update_block("persona", "Test")
            status = store.get_status()
            assert len(status) == 4
            assert all("label" in s and "chars" in s and "max_chars" in s for s in status)

    def test_nonexistent_block(self):
        from agent.memory_blocks import MemoryBlockStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = MemoryBlockStore(hermes_home=tmpdir)
            result = store.update_block("nonexistent", "content")
            assert result["success"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# Enhanced Output Truncation Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestOutputTruncation:
    """Tests for agent/output_truncation.py"""

    def test_short_text_unchanged(self):
        from agent.output_truncation import smart_truncate

        text = "Hello, world!"
        result = smart_truncate(text, max_chars=1000)
        assert result == text

    def test_truncate_by_chars_head_tail(self):
        from agent.output_truncation import smart_truncate

        text = "A" * 1000
        result = smart_truncate(text, max_chars=100, strategy="head_tail")
        assert len(result) < 1000
        assert "omitted" in result
        assert "chars" in result

    def test_truncate_by_chars_head(self):
        from agent.output_truncation import smart_truncate

        text = "A" * 1000
        result = smart_truncate(text, max_chars=100, strategy="head")
        assert result.startswith("A" * 100)
        assert "omitted" in result

    def test_truncate_by_chars_tail(self):
        from agent.output_truncation import smart_truncate

        text = "A" * 1000
        result = smart_truncate(text, max_chars=100, strategy="tail")
        assert result.endswith("A" * 100)
        assert "omitted" in result

    def test_truncate_by_lines(self):
        from agent.output_truncation import smart_truncate

        text = "\n".join(f"Line {i}" for i in range(200))
        result = smart_truncate(text, max_chars=100000, max_lines=20)
        assert "omitted" in result
        assert "200 lines" in result

    def test_context_hint_included(self):
        from agent.output_truncation import smart_truncate

        text = "A" * 1000
        result = smart_truncate(text, max_chars=100, context_hint="test output")
        assert "test output" in result

    def test_tool_result_truncation(self):
        from agent.output_truncation import truncate_tool_result

        long_output = "x\n" * 500
        result = truncate_tool_result(long_output, "execute_bash", max_chars=200)
        assert "omitted" in result
        # Should include tool-specific hint
        assert "head" in result.lower() or "tail" in result.lower() or "redirect" in result.lower()

    def test_empty_text_unchanged(self):
        from agent.output_truncation import smart_truncate

        assert smart_truncate("") == ""
        assert smart_truncate("", max_chars=10) == ""


# ═══════════════════════════════════════════════════════════════════════════════
# Microcompact Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestMicrocompact:
    """Tests for agent/microcompact.py"""

    def test_empty_messages(self):
        from agent.microcompact import microcompact_messages

        assert microcompact_messages([]) == []

    def test_preserves_system_message(self):
        from agent.microcompact import microcompact_messages

        messages = [
            {"role": "system", "content": "You are helpful."},
            {"role": "user", "content": "Hello"},
        ]
        result = microcompact_messages(messages)
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are helpful."

    def test_strips_thinking_blocks(self):
        from agent.microcompact import microcompact_messages

        messages = [
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "<think>Let me calculate...</think>The answer is 4."},
            {"role": "user", "content": "Thanks"},
            {"role": "assistant", "content": "You're welcome!"},
        ]
        result = microcompact_messages(messages, protect_last_n=1)
        # The old assistant message should have thinking stripped
        assistant_msg = [m for m in result if m["role"] == "assistant"][0]
        assert "<think>" not in assistant_msg["content"]
        assert "The answer is 4." in assistant_msg["content"]

    def test_truncates_old_tool_results(self):
        from agent.microcompact import microcompact_messages

        messages = [
            {"role": "user", "content": "Read the file"},
            {"role": "assistant", "content": "Reading...", "tool_calls": [{"id": "1", "function": {"name": "read_file", "arguments": "{}"}}]},
            {"role": "tool", "name": "read_file", "content": "x" * 5000},
            {"role": "assistant", "content": "Done"},
            {"role": "user", "content": "Thanks"},  # Protected tail
        ]
        result = microcompact_messages(messages, protect_last_n=1, max_tool_result_chars=100)
        tool_msg = [m for m in result if m.get("role") == "tool"]
        if tool_msg:
            assert len(tool_msg[0]["content"]) < 5000

    def test_removes_empty_tool_results(self):
        from agent.microcompact import microcompact_messages

        messages = [
            {"role": "user", "content": "Do something"},
            {"role": "tool", "name": "write_file", "content": "ok"},
            {"role": "assistant", "content": "Done"},
            {"role": "user", "content": "Next"},  # Protected
        ]
        result = microcompact_messages(messages, protect_last_n=1, strip_empty_tool_results=True)
        tool_msgs = [m for m in result if m.get("role") == "tool"]
        assert len(tool_msgs) == 0  # "ok" result removed

    def test_protects_tail(self):
        from agent.microcompact import microcompact_messages

        messages = [
            {"role": "user", "content": "Old message"},
            {"role": "assistant", "content": "<think>old thinking</think>Old response"},
            {"role": "user", "content": "Recent message"},
            {"role": "assistant", "content": "<think>recent thinking</think>Recent response"},
        ]
        result = microcompact_messages(messages, protect_last_n=2)
        # Last 2 messages should only have thinking stripped (light touch)
        # but content preserved
        assert any("Recent response" in m.get("content", "") for m in result)

    def test_estimate_savings(self):
        from agent.microcompact import estimate_savings

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "<think>Long thinking block here</think>Short answer"},
            {"role": "tool", "name": "bash", "content": "x" * 2000},
            {"role": "user", "content": "Recent"},
        ]
        savings = estimate_savings(messages, protect_last_n=1)
        assert savings["thinking_chars"] > 0
        assert savings["tool_result_chars"] > 0
        assert savings["total_chars"] > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Cache-Stable Prompt Ordering Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestCacheStablePrompt:
    """Tests for agent/prompt_cache_stable.py"""

    def test_stable_before_volatile(self):
        from agent.prompt_cache_stable import CacheStablePromptBuilder

        builder = CacheStablePromptBuilder()
        builder.add_stable("Identity section", "identity")
        builder.add_stable("Skills section", "skills")
        builder.add_volatile("Memory snapshot", "memory")
        builder.add_volatile("Current time: now", "datetime")

        prompt = builder.build()
        identity_pos = prompt.find("Identity section")
        memory_pos = prompt.find("Memory snapshot")
        assert identity_pos < memory_pos

    def test_cache_hash_stable(self):
        from agent.prompt_cache_stable import CacheStablePromptBuilder

        builder = CacheStablePromptBuilder()
        builder.add_stable("Same content")
        hash1 = builder.get_stable_hash()

        builder.reset()
        builder.add_stable("Same content")
        hash2 = builder.get_stable_hash()

        assert hash1 == hash2

    def test_cache_invalidation_detection(self):
        from agent.prompt_cache_stable import CacheStablePromptBuilder

        builder = CacheStablePromptBuilder()
        builder.add_stable("Version 1")
        builder.would_invalidate_cache()  # First call sets baseline

        builder.reset()
        builder.add_stable("Version 2")  # Changed!
        assert builder.would_invalidate_cache() is True

    def test_volatile_changes_dont_invalidate(self):
        from agent.prompt_cache_stable import CacheStablePromptBuilder

        builder = CacheStablePromptBuilder()
        builder.add_stable("Stable content")
        builder.add_volatile("Time: 12:00")
        builder.would_invalidate_cache()  # Set baseline

        builder.reset()
        builder.add_stable("Stable content")  # Same!
        builder.add_volatile("Time: 12:05")  # Changed but volatile
        assert builder.would_invalidate_cache() is False

    def test_cache_ratio(self):
        from agent.prompt_cache_stable import CacheStablePromptBuilder

        builder = CacheStablePromptBuilder()
        builder.add_stable("A" * 800)
        builder.add_volatile("B" * 200)
        ratio = builder.cache_ratio
        assert 0.7 < ratio < 0.9  # ~80% stable

    def test_convenience_function(self):
        from agent.prompt_cache_stable import reorder_system_prompt_for_cache_stability

        prompt = reorder_system_prompt_for_cache_stability(
            identity="I am Hermes",
            skills_guidance="Available skills: ...",
            memory_snapshot="User prefers Python",
            datetime_info="2026-05-17",
        )
        assert "I am Hermes" in prompt
        assert "Available skills" in prompt
        assert "User prefers Python" in prompt
        # Identity should come before memory
        assert prompt.find("I am Hermes") < prompt.find("User prefers Python")

    def test_empty_sections_skipped(self):
        from agent.prompt_cache_stable import reorder_system_prompt_for_cache_stability

        prompt = reorder_system_prompt_for_cache_stability(
            identity="I am Hermes",
            skills_guidance="",  # Empty — should be skipped
            memory_snapshot="",  # Empty — should be skipped
        )
        assert "I am Hermes" in prompt
        assert "skills" not in prompt.lower()


# ═══════════════════════════════════════════════════════════════════════════════
# kiro-cli Provider Tests
# ═══════════════════════════════════════════════════════════════════════════════


class TestKiroCliProvider:
    """Tests for providers/kiro_cli.py"""

    def test_profile_creation(self):
        from providers.kiro_cli import KiroCliProfile

        profile = KiroCliProfile()
        assert profile.name == "kiro-cli"
        assert "kiro" in profile.aliases
        assert profile.supports_health_check is False

    def test_fetch_models(self):
        from providers.kiro_cli import KiroCliProfile

        profile = KiroCliProfile()
        models = profile.fetch_models()
        assert models is not None
        assert "claude-opus-4.6" in models
        assert "claude-sonnet-4.6" in models
        assert len(models) >= 10

    def test_context_lengths(self):
        from providers.kiro_cli import get_context_length

        assert get_context_length("claude-opus-4.6") == 1_000_000
        assert get_context_length("claude-sonnet-4.6") == 1_000_000
        assert get_context_length("claude-haiku-4.5") == 200_000
        assert get_context_length("unknown-model") == 200_000  # default

    def test_max_output_tokens(self):
        from providers.kiro_cli import get_max_output_tokens

        assert get_max_output_tokens("claude-opus-4.6") == 32_000
        assert get_max_output_tokens("claude-haiku-4.5") == 8_192

    def test_is_available(self):
        from providers.kiro_cli import is_available

        # This depends on whether kiro-cli is installed
        result = is_available()
        assert isinstance(result, bool)
