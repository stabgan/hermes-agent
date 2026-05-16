# Bug Report — Hermes Agent Code Audit

**Date:** 2025-07-17  
**Scope:** lint_guard.py, role_profiles.py, memory_blocks.py, output_truncation.py, microcompact.py, prompt_cache_stable.py, kiro_cli.py (provider), api.py (wrapper), test_integrations.py

---

## Critical Severity

### 1. Command Injection via Filepath — `lint_guard.py` (Lines 79-82, YAML linter)

**File:** `agent/lint_guard.py`, lines 79-82  
**Bug:** The YAML linter uses `open(sys.argv[1])` inside a `python3 -c` command. The filepath is appended to the command list (line 143: `full_cmd = list(command) + [target_path]`). While `subprocess.run` with a list avoids shell injection, the Python code inside the `-c` string uses `sys.argv[1]` which is safe from injection. However, the real issue is that `open(sys.argv[1])` does **no path validation** — an attacker-controlled filename could read arbitrary files via path traversal (e.g., `../../etc/passwd`).

**Severity:** Critical  
**Fix:** Validate that `filepath` is within the expected workspace before linting. Add path canonicalization and bounds checking.

---

### 2. Subprocess Injection via Unsanitized Model Name — `api.py` (Line 100) & `kiro_cli.py` (Line 186)

**File:** `kiro-openai-wrapper/api.py`, line 100; `providers/kiro_cli.py`, line 186  
**Bug:** `build_command(model)` passes the user-supplied `model` string directly into the subprocess command list (`["--model", model]`). While the API endpoint does validate against `AVAILABLE_MODELS` (line 107), the `build_command` function itself has no validation. If called from any other code path with an unsanitized model string containing shell metacharacters or `--` flags, it could inject arbitrary CLI flags. In `api.py`, the model validation at line 107 uses a fallback (`else "claude-sonnet-4.6"`) but the check is `if request.model in [m["id"] for m in AVAILABLE_MODELS]` — this means an invalid model silently falls back rather than being rejected, which could mask bugs.

**Severity:** Critical (in `api.py` — external-facing endpoint); Medium (in `kiro_cli.py` — internal use)  
**Fix:** Validate model against an allowlist in `build_command()` itself, not just at the caller. Reject unknown models with an error rather than silently falling back.

---

### 3. Resource Leak — Subprocess Not Killed on Error in Streaming — `api.py` (Lines 119-165) & `kiro_cli.py` (Lines 240-300)

**File:** `kiro-openai-wrapper/api.py`, lines 119-165; `providers/kiro_cli.py`, lines 240-300  
**Bug:** In `stream_response()` and `_stream_completion()`, if an exception occurs after `subprocess.Popen` but before `process.wait()`, the subprocess is never killed. The `except` block yields an error chunk but does not call `process.kill()` or `process.terminate()`. This leads to zombie processes accumulating.

**Severity:** Critical  
**Fix:** Wrap the streaming logic in a `try/finally` block that calls `process.kill()` and `process.wait()` on any exit path. Example:
```python
try:
    # ... streaming logic ...
finally:
    if process.poll() is None:
        process.kill()
        process.wait()
```

---

### 4. Unread stderr Pipe Causes Potential Deadlock — `kiro_cli.py` (Lines 240-250) & `api.py` (Lines 125-130)

**File:** `providers/kiro_cli.py`, lines 240-250; `kiro-openai-wrapper/api.py`, lines 125-130  
**Bug:** `subprocess.Popen` is called with `stderr=subprocess.PIPE` but stderr is never read. If the subprocess writes enough to stderr to fill the OS pipe buffer (typically 64KB), the process will block on the write and deadlock. The stdout read loop will then hang forever waiting for the process to exit.

**Severity:** Critical  
**Fix:** Either redirect stderr to `subprocess.DEVNULL`, or read stderr in a separate thread, or use `stderr=subprocess.STDOUT` to merge streams.

---

## High Severity

### 5. f-string Missing `f` Prefix — `kiro_cli.py` (Line 225)

**File:** `providers/kiro_cli.py`, line 225  
**Bug:** The timeout error message uses a regular string instead of an f-string:
```python
content = "[Response timed out after {self.timeout}s]"
```
This will literally output `{self.timeout}s` instead of the actual timeout value.

**Severity:** High  
**Fix:** Change to `f"[Response timed out after {self.timeout}s]"`

---

### 6. Race Condition — `would_invalidate_cache()` Not Thread-Safe — `prompt_cache_stable.py` (Lines 93-107)

**File:** `agent/prompt_cache_stable.py`, lines 93-107  
**Bug:** `would_invalidate_cache()` reads and writes `self._last_stable_hash` without any locking. If called from multiple threads (e.g., concurrent API requests), the check-then-set pattern is racy. One thread could read the old hash while another is updating it.

**Severity:** High (if used in multi-threaded context)  
**Fix:** Use a `threading.Lock` to protect `_last_stable_hash` access, or document that the class is not thread-safe.

---

### 7. `fcntl` Import Fails on Windows — `api.py` (Line 120) & `kiro_cli.py` (Line 241)

**File:** `kiro-openai-wrapper/api.py`, line 120; `providers/kiro_cli.py`, line 241  
**Bug:** `import fcntl` is used inside the streaming functions. `fcntl` is a Unix-only module and will raise `ModuleNotFoundError` on Windows. The import is inside the function body so it won't fail at module load, but streaming will be completely broken on Windows.

**Severity:** High  
**Fix:** Add a platform check and fall back to a threaded reader on Windows, or document that streaming requires Unix. At minimum, catch the import error gracefully.

---

### 8. Mutable Default in Module-Level Dict — `role_profiles.py` (Global `ROLE_PROFILES` and `AVAILABLE_ROLES`)

**File:** `agent/role_profiles.py`, lines 155-156 and `register_role()` function  
**Bug:** `register_role()` mutates the module-level `ROLE_PROFILES` dict and `AVAILABLE_ROLES` list. These are shared global state. In a multi-tenant or test environment, registering a custom role in one test pollutes all subsequent tests. The test `test_register_custom_role` in `test_integrations.py` does exactly this — it registers "security-auditor" permanently, affecting other test runs.

**Severity:** High  
**Fix:** Provide a way to scope role registrations (e.g., a context manager or instance-based registry). At minimum, add cleanup in tests.

---

### 9. Memory Blocks — Path Traversal via Block Label — `memory_blocks.py` (Line 119)

**File:** `agent/memory_blocks.py`, line 119  
**Bug:** `load_from_disk()` constructs file paths using `self._blocks_dir / f"{label}.md"`. The labels come from `DEFAULT_BLOCKS` (safe), but `update_block()` accepts any label from the `self.blocks` dict. If a custom block with a label like `"../../../etc/passwd"` were registered, it could read/write outside the intended directory. Currently only default labels are used, but the API doesn't validate labels.

**Severity:** High (latent — exploitable if custom blocks are added)  
**Fix:** Validate that labels contain only alphanumeric characters and underscores. Add: `if not re.match(r'^[a-z_]+$', label): raise ValueError(...)`

---

### 10. Token Count Estimation is Inaccurate — `api.py` (Line 113) & `kiro_cli.py` (Line 233)

**File:** `kiro-openai-wrapper/api.py`, line 113; `providers/kiro_cli.py`, line 233  
**Bug:** Token usage is estimated using `len(prompt.split())` (word count). This is a very rough approximation — actual tokenization produces ~1.3x more tokens than word count for English text, and much more for code. Clients relying on the `usage` field for billing, rate limiting, or context window management will get incorrect values.

**Severity:** High (API contract violation — OpenAI clients expect accurate token counts)  
**Fix:** Use `tiktoken` or a similar tokenizer for accurate counts, or clearly mark the usage field as estimated (e.g., add an `"estimated": true` field).

---

## Medium Severity

### 11. `microcompact_messages` Breaks OpenAI Tool Call Protocol — `microcompact.py` (Lines 148-155)

**File:** `agent/microcompact.py`, lines 148-155  
**Bug:** When `strip_empty_tool_results=True`, tool result messages with content like "ok" are removed entirely. However, the OpenAI API requires that every `tool_calls` entry in an assistant message has a corresponding `tool` role message with a matching `tool_call_id`. Removing the tool result message without also removing the corresponding tool call creates an invalid message sequence that will cause API errors.

**Severity:** Medium  
**Fix:** When removing a tool result message, also remove (or mark) the corresponding tool call in the preceding assistant message. Or keep a stub message with the correct `tool_call_id`.

---

### 12. `_truncate_content` Doesn't Handle Non-Text List Items Correctly — `microcompact.py` (Lines 68-85)

**File:** `agent/microcompact.py`, lines 68-85  
**Bug:** In `_truncate_content`, when content is a list, non-text items (e.g., `tool_result`, `image_url`) are appended without counting their size against `remaining`. This means the total output could exceed `max_chars` if there are many non-text items.

**Severity:** Medium  
**Fix:** Count the size of non-text items against the remaining budget, or at minimum document that the limit applies only to text parts.

---

### 13. `MemoryBlock.usage_pct` Division by Zero Protection is Incomplete — `memory_blocks.py` (Line 50)

**File:** `agent/memory_blocks.py`, line 50  
**Bug:** `usage_pct` returns `0.0` when `max_chars == 0`, but a block with `max_chars=0` would make `update()` and `append()` always return `False` (since any content length > 0). This is an inconsistent state — the block is unusable but reports 0% usage.

**Severity:** Medium (edge case — no default blocks have max_chars=0)  
**Fix:** Either disallow `max_chars=0` in the constructor, or return `100.0` when `max_chars == 0` and content is non-empty.

---

### 14. `smart_truncate` Unreachable Code Path — `output_truncation.py` (Line 63)

**File:** `agent/output_truncation.py`, line 63  
**Bug:** The final `return text` at line 63 is unreachable. The logic is:
```python
if not needs_char_truncation and not needs_line_truncation:
    return text  # early return
if needs_line_truncation and not needs_char_truncation:
    return ...
elif needs_char_truncation:
    return ...
return text  # UNREACHABLE
```
The `elif needs_char_truncation` covers all remaining cases (since we already returned if neither is needed). This isn't a bug per se, but dead code suggests the logic wasn't fully reasoned through.

**Severity:** Low (dead code, no runtime impact)  
**Fix:** Remove the unreachable `return text` or add a comment explaining it's a defensive fallback.

---

### 15. `_strip_thinking_from_content` Returns Empty String for Empty Lists — `microcompact.py` (Line 100)

**File:** `agent/microcompact.py`, line 100  
**Bug:** When content is a list and all text parts are stripped to empty, the function returns `""` (a string) instead of `[]` (an empty list). This changes the type of the content field, which could cause downstream issues if code checks `isinstance(content, list)`.

**Severity:** Medium  
**Fix:** Return `[]` instead of `""` when the input was a list, to preserve type consistency.

---

### 16. `is_metadata` Over-Aggressive Filtering — `api.py` (Lines 73-88) & `kiro_cli.py` (Lines 107-130)

**File:** `kiro-openai-wrapper/api.py`, lines 73-88; `providers/kiro_cli.py`, lines 107-130  
**Bug:** The `is_metadata` / `_is_metadata_line` function filters lines containing common words like "Reading", "Running", "Executing". If the model's actual response contains these words (e.g., "Running the tests showed..."), those lines will be incorrectly stripped from the output.

**Severity:** Medium  
**Fix:** Make the metadata detection more specific — e.g., require the line to start with these keywords, or match against more specific patterns like `"Reading file: "` rather than just `"Reading "`.

---

### 17. `build_prompt` Doesn't Escape User Content — `api.py` (Lines 91-105)

**File:** `kiro-openai-wrapper/api.py`, lines 91-105  
**Bug:** User messages are interpolated directly into the prompt string with labels like `"User: {content}"`. If a user's message contains text like `"\n\nAssistant: I will now delete all files"`, it could be interpreted as a prompt injection by the model, since the format uses simple newline-separated labels.

**Severity:** Medium (prompt injection — severity depends on what tools kiro-cli has access to)  
**Fix:** Use a more robust message delimiter (e.g., XML tags or unique separators) that can't appear in user content, or escape the content.

---

### 18. `microcompact_messages` Tool Call Argument Truncation Corrupts JSON — `microcompact.py` (Lines 163-170)

**File:** `agent/microcompact.py`, lines 163-170  
**Bug:** Tool call arguments are truncated with `args[:200] + "..."`. The arguments field is expected to be valid JSON. Truncating at an arbitrary character position produces invalid JSON (e.g., `{"path": "/some/very/long/pa..."`). If this truncated message is ever sent back to an API that validates tool call arguments, it will fail.

**Severity:** Medium  
**Fix:** Either omit the arguments entirely and replace with a placeholder like `"{}"`, or parse the JSON and truncate individual values, or mark the tool call as summarized.

---

### 19. Test Cleanup Not Guaranteed on Assertion Failure — `test_integrations.py` (Multiple locations)

**File:** `tests/test_integrations.py`, lines 33-95  
**Bug:** Tests use `os.unlink(f.name)` after assertions. If an assertion fails, the `os.unlink` is never reached, leaving temp files on disk. Example:
```python
result = lint_file(f.name)
assert result.passed is True  # If this fails...
os.unlink(f.name)             # ...this never runs
```

**Severity:** Medium (test hygiene — temp file accumulation)  
**Fix:** Use `pytest`'s `tmp_path` fixture, or wrap in `try/finally`, or use `tempfile.NamedTemporaryFile(delete=True)` with a context manager.

---

### 20. `CacheStablePromptBuilder.reset()` Doesn't Reset `_last_stable_hash` — `prompt_cache_stable.py` (Lines 109-112)

**File:** `agent/prompt_cache_stable.py`, lines 109-112  
**Bug:** `reset()` clears `_stable_sections` and `_volatile_sections` but does NOT reset `_last_stable_hash`. This means after a reset, `would_invalidate_cache()` will compare the new (empty) stable hash against the old hash, incorrectly reporting cache invalidation even if the intent was to rebuild from scratch.

**Severity:** Medium  
**Fix:** Add `self._last_stable_hash = None` to the `reset()` method.

---

### 21. Non-Blocking Read May Miss Final Output — `api.py` & `kiro_cli.py` (Streaming)

**File:** `kiro-openai-wrapper/api.py`, lines 140-150; `providers/kiro_cli.py`, lines 265-275  
**Bug:** The streaming loop checks `process.poll()` and then tries to read. There's a TOCTOU race: the process could exit between `poll()` returning `None` and the `read()` call. More critically, when `poll()` returns a non-None value (process exited), the loop breaks immediately. But there may still be unread data in the pipe buffer that was written before the process exited. The code should do a final drain read after the loop exits.

**Severity:** Medium  
**Fix:** After the while loop breaks due to `retcode is not None`, do a final blocking read to drain any remaining data from the pipe.

---

## Low Severity

### 22. `MemoryBlockStore._initialize_defaults` Creates Copies Without `last_modified` — `memory_blocks.py` (Lines 108-115)

**File:** `agent/memory_blocks.py`, lines 108-115  
**Bug:** `_initialize_defaults` copies fields from `DEFAULT_BLOCKS` but doesn't copy `last_modified`. Since `last_modified` defaults to `0.0` in the dataclass, this is fine, but it means the `DEFAULT_BLOCKS` dict entries are never used directly — they're template objects. If someone modifies `DEFAULT_BLOCKS` at runtime expecting it to affect existing stores, it won't.

**Severity:** Low  
**Fix:** Document that `DEFAULT_BLOCKS` is a template, not a live reference.

---

### 23. `lint_file` Uses `path.parent` for `cwd` Without Checking It Exists — `lint_guard.py` (Line 147)

**File:** `agent/lint_guard.py`, line 147  
**Bug:** `cwd=str(path.parent) if path.parent.exists() else None` — if `content` is provided and a temp file is used, `path` still refers to the original filepath. The `cwd` is set based on the original file's parent directory, not the temp file's location. This means the linter runs in the original file's directory context, which is probably intentional for resolving imports, but could be confusing if the original path doesn't exist yet (e.g., linting content for a file that hasn't been created).

**Severity:** Low  
**Fix:** When using a temp file, consider whether `cwd` should be the temp file's directory or the target file's directory. Add a comment explaining the choice.

---

### 24. `get_role_for_task` Keyword Matching is Order-Dependent — `role_profiles.py` (Lines 175-195)

**File:** `agent/role_profiles.py`, lines 175-195  
**Bug:** The keyword matching uses sequential `if/elif`-style logic (actually sequential `if` with early returns). A task like "review and fix the bug" would match "reviewer" (because "review" comes first in the check order) even though "debugger" might be more appropriate given "fix" and "bug" are also present.

**Severity:** Low  
**Fix:** Consider a scoring system that counts keyword matches per role and returns the highest-scoring role, rather than first-match-wins.

---

### 25. `estimate_savings` Hardcodes 500 as Threshold — `microcompact.py` (Line 213)

**File:** `agent/microcompact.py`, line 213  
**Bug:** `estimate_savings` hardcodes `if content_len > 500` as the threshold for counting tool result savings. But `microcompact_messages` accepts `max_tool_result_chars` as a parameter (default 500). If a caller uses a different threshold, the estimate will be inaccurate.

**Severity:** Low  
**Fix:** Accept `max_tool_result_chars` as a parameter in `estimate_savings()` to match the actual compaction behavior.

---

### 26. `truncate_tool_result` Doesn't Check Line Count Independently — `output_truncation.py` (Lines 131-133)

**File:** `agent/output_truncation.py`, lines 131-133  
**Bug:** The early return check is `if not result or (len(result) <= max_chars and result.count("\n") <= max_lines)`. Using `result.count("\n")` counts newline characters, but a file with N newlines has N+1 lines. This is an off-by-one: a result with exactly `max_lines` newlines actually has `max_lines + 1` lines but passes the check.

**Severity:** Low  
**Fix:** Use `result.count("\n") + 1 <= max_lines` or compare against `max_lines - 1` newlines.

---

### 27. `KiroCliProfile` Sets `base_url` to Localhost Wrapper — `kiro_cli.py` (Line 163)

**File:** `providers/kiro_cli.py`, line 163  
**Bug:** `base_url="http://localhost:8000/v1"` is set as a fallback. This is the URL of the separate OpenAI wrapper service. If the base class's `fetch_models()` is ever called (bypassing the override), it would try to connect to localhost:8000 which may not be running, causing confusing timeout errors.

**Severity:** Low  
**Fix:** Set `base_url=""` since this provider doesn't use HTTP, and rely on the overridden `fetch_models()`.

---

### 28. MD5 Used for Hashing — `prompt_cache_stable.py` (Line 90)

**File:** `agent/prompt_cache_stable.py`, line 90  
**Bug:** `hashlib.md5` is used for the stable hash. While this isn't a security context (it's for cache invalidation detection), MD5 is deprecated and some environments (FIPS-compliant) disable it entirely, which would cause a runtime error.

**Severity:** Low  
**Fix:** Use `hashlib.sha256` with truncation instead: `hashlib.sha256(...).hexdigest()[:12]`

---

### 29. `_content_char_count` Doesn't Handle All Content Types — `microcompact.py` (Lines 42-55)

**File:** `agent/microcompact.py`, lines 42-55  
**Bug:** `_content_char_count` handles `str` and `list` but returns `0` for any other type (e.g., `None`, `int`, `dict`). If a message has `content: None` (valid in OpenAI API for assistant messages with tool_calls), the function returns 0, which is correct. But if content is unexpectedly a dict or other type, it silently returns 0 rather than raising, which could mask bugs.

**Severity:** Low  
**Fix:** Add a debug log when an unexpected content type is encountered.

---

### 30. Test `test_register_custom_role` Pollutes Global State — `test_integrations.py` (Lines 175-185)

**File:** `tests/test_integrations.py`, lines 175-185  
**Bug:** This test calls `register_role(custom)` which permanently modifies the global `ROLE_PROFILES` and `AVAILABLE_ROLES`. If tests run in a specific order, later tests that check `len(AVAILABLE_ROLES)` or iterate over roles will see the extra "security-auditor" role. The `test_list_roles` test uses `assert len(roles) >= 8` which masks this issue.

**Severity:** Low (test isolation issue)  
**Fix:** Add a teardown that removes the registered role, or use `monkeypatch` to restore the original state.

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 4     |
| High     | 6     |
| Medium   | 11    |
| Low      | 9     |
| **Total**| **30**|

### Top Priority Fixes
1. Kill subprocess on streaming errors (resource leak / zombie processes)
2. Drain stderr or redirect to DEVNULL (deadlock risk)
3. Fix f-string bug in timeout message (incorrect user-facing output)
4. Fix tool result removal breaking OpenAI protocol (API errors)
5. Fix `reset()` not clearing `_last_stable_hash` (incorrect cache invalidation)
