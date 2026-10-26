# Saturate Pipeline Bugfixes

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 bugs in the saturation pipeline — 2 crash-causing, 3 logic errors, 1 API gap.

**Architecture:** Surgical fixes to `backend/saturate.py` and `backend/server.py`. No new files. All fixes are additive type guards, bounds checks, or parameter additions.

**Tech Stack:** Python 3.12, FastAPI/Pydantic, async generators

---

### Task 1: Fix `add_contractors` string crash in `_merge_schematic`

**Files:**
- Modify: `backend/saturate.py:260-267`

**Bug:** LLM can return `"add_contractors": ["ORNL", "Sandia"]` (strings) instead of dicts. `c.get("name", "")` crashes with `AttributeError: 'str' object has no attribute 'get'`.

- [ ] **Step 1: Add string-to-dict coercion for contractors**

```python
# In _merge_schematic, enrichment add_contractors loop (line 260)
for c in add_contractors:
    if isinstance(c, str):
        c = {"name": c, "role": "unknown"}
    if not isinstance(c, dict):
        continue
    cname = c.get("name", "").lower()
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('backend/saturate.py').read()); print('OK')"`

---

### Task 2: Fix `add_equipment` dict crash in `_merge_schematic`

**Files:**
- Modify: `backend/saturate.py:246-250`

**Bug:** LLM can return `[{"name": "furnace", "model": "X"}]` (dicts) instead of strings. `e.lower()` crashes with `AttributeError`.

- [ ] **Step 1: Add type coercion for equipment items**

```python
# In _merge_schematic, enrichment add_equipment loop (line 246)
for e in add_equip:
    if isinstance(e, dict):
        e = e.get("name", "") or str(e)
    if not isinstance(e, str) or not e:
        continue
    if e.lower() not in existing_equip_lower:
```

- [ ] **Step 2: Verify syntax**

Run: `python3 -c "import ast; ast.parse(open('backend/saturate.py').read()); print('OK')"`

---

### Task 3: Add depth limit to auto-explore

**Files:**
- Modify: `backend/saturate.py:313-317` (signature)
- Modify: `backend/saturate.py:357-358` (loop guard)

**Bug:** `while True` loop with no max depth — can run indefinitely if LLM keeps hallucinating new sub-steps.

- [ ] **Step 1: Add `max_depth` parameter to `saturate()` signature**

```python
async def saturate(
    self,
    query: str,
    max_passes: int | None = None,
    auto_explore: bool = True,
    max_depth: int = 3,
) -> AsyncGenerator[dict, None]:
```

- [ ] **Step 2: Add depth guard at top of while loop**

```python
# --- Phase 2+: Recursive auto-explore ---
while True:
    depth += 1
    if depth > max_depth:
        yield self._evt("status", {
            "stage": "explore_done",
            "message": f"Auto-explore reached max depth ({max_depth}). Stopping.",
        })
        break
    # Find unexplored steps
```

- [ ] **Step 3: Verify syntax**

---

### Task 4: Fix Hermes partial-stream fallback

**Files:**
- Modify: `backend/saturate.py:598-610`

**Bug:** If Hermes streams partial tokens then crashes, `fell_back` stays `False` (because `response_parts` is non-empty), so Ollama fallback never fires. Result: truncated response used for extraction.

- [ ] **Step 1: Always fall back on Hermes exception, clear partial state**

```python
fell_back = False
if use_hermes:
    try:
        async for token in self.hermes.chat_stream(messages):
            response_parts.append(token)
            yield self._evt("token", {"content": token})
    except Exception:
        # Always fall back — partial output is worse than full retry
        response_parts.clear()
        fell_back = True
if not use_hermes or fell_back:
    if fell_back:
        yield self._evt("token", {"content": "\n\n[Connection lost — retrying with local model...]\n\n"})
    async for token in self.ollama.chat_stream(messages):
        response_parts.append(token)
        yield self._evt("token", {"content": token})
```

- [ ] **Step 2: Verify syntax**

---

### Task 5: Use `label` parameter in status messages

**Files:**
- Modify: `backend/saturate.py:481-484` (saturate_start)
- Modify: `backend/saturate.py:497-499` (saturate_search)
- Modify: `backend/saturate.py:764-770` (saturate_done)

**Bug:** `label` parameter accepted by `_saturate_query` but never used — provides no context for which sub-query is running during auto-explore.

- [ ] **Step 1: Add label prefix to key status messages**

After the `seen_contract_keys` init block, add:
```python
prefix = f"[{label}] " if label else ""
```

Then update the `saturate_start` message:
```python
yield self._evt("status", {
    "stage": "saturate_start",
    "message": f"{prefix}Saturation mode — searching until knowledge is exhausted",
})
```

And `saturate_search`:
```python
"message": f"{prefix}Pass {pass_num} — Searching contracts (vector + keyword + graph)...",
```

And `saturate_done`:
```python
"message": (
    f"{prefix}Knowledge saturated after {pass_num} passes. "
```

- [ ] **Step 2: Verify syntax**

---

### Task 6: Expose `auto_explore` and `max_depth` in API

**Files:**
- Modify: `backend/server.py:525-527` (request model)
- Modify: `backend/server.py:548` (handler call)

**Bug:** `SaturateChatRequest` doesn't expose `auto_explore` or `max_depth`, so frontend cannot control the new feature.

- [ ] **Step 1: Update request model**

```python
class SaturateChatRequest(BaseModel):
    messages: list[dict]
    max_passes: int | None = None
    auto_explore: bool = True
    max_depth: int = 3
```

- [ ] **Step 2: Pass new params to pipeline**

```python
async for event in pipeline.saturate(
    user_msg,
    max_passes=req.max_passes,
    auto_explore=req.auto_explore,
    max_depth=req.max_depth,
):
```

- [ ] **Step 3: Verify syntax**

---

### Task 7: Final verification

- [ ] **Step 1:** Run syntax check on both files
- [ ] **Step 2:** Commit all fixes
