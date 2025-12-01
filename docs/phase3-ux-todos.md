# GADS Phase 3: UX Improvements TODO

## Status: In Progress

## Critical Bugs

### 1. ✅ Approval Prompt Blocked by Spinner (FIXED)
**Priority:** HIGH

**Problem:** `console.status` spinner blocks input while approval prompt is shown. User sees "requires approval. Proceed?" but cannot type response.

**Solution:** Removed spinner wrapper around entire pipeline execution. Instead:
- Progress callback pattern: orchestrator emits events, CLI handles display
- Spinner starts/stops around each LLM call, not the whole pipeline
- Spinner explicitly stopped before approval prompts

**Files Changed:**
- `src/gads/orchestrator/core.py` - Added `PipelineEvent` class and `progress_callback` parameter
- `src/gads/cli.py` - Rewrote `pipeline_run()` with event-driven progress display

---

## UX Improvements

### 2. ✅ No Progress Feedback During Pipeline (FIXED)
**Priority:** MEDIUM

**Problem:** Pipeline runs for 5+ minutes showing only "Running pipeline..." with no indication of what's happening.

**Solution:** Real-time step-by-step progress via progress callback:
```
Step 1/4: concept (architect)
  ✓ Complete (1,234 in / 567 out, $0.0543)

Step 2/4: architecture (architect)
  → Calling LLM...
```

**Files Changed:**
- `src/gads/orchestrator/core.py` - Emits events at key points
- `src/gads/cli.py` - `handle_progress()` callback displays events

---

### 3. ✅ No Agent List at Startup (FIXED)
**Priority:** LOW

**Problem:** Log says "Orchestrator initialized with 5 agents" but doesn't name them.

**Solution:** Added agent names to log:
```
Orchestrator initialized with 5 agents: architect, designer, developer_2d, developer_3d, qa
```

**Files Changed:**
- `src/gads/orchestrator/core.py` - Updated `__init__` logging

---

### 4. ✅ No Cost/Token Tracking Display (FIXED)
**Priority:** MEDIUM

**Problem:** Anthropic API calls don't show token counts or estimated costs.

**Solution:** Token usage now displayed per-step and in final summary:
- Per step: `✓ Complete (1,234 in / 567 out, $0.0543)`
- Summary: `Tokens: 5,432 in / 2,341 out` and `Estimated cost: $0.1234`

**Note:** Infrastructure already existed (`TokenUsage` class with `estimate_cost()`), just needed CLI integration.

**Files Changed:**
- `src/gads/cli.py` - Accumulates and displays token usage

---

### 5. ✅ No Output Until Pipeline Completes/Fails (FIXED)
**Priority:** MEDIUM

**Problem:** Even successful steps show "No output captured" if pipeline fails later. User has no idea what work was done.

**Solution:** 
- Real-time progress shows each step's completion immediately
- On failure, the `PIPELINE_FAILED` event includes `completed_steps` list
- Summary shows completed steps even on failure/cancellation

**Files Changed:**
- `src/gads/orchestrator/core.py` - Events include completion info
- `src/gads/cli.py` - Shows completed steps on failure

---

## Implementation Summary

All Phase 3 UX improvements are now complete:

1. **Progress Callback Pattern**: `run_pipeline()` accepts `progress_callback` parameter
2. **PipelineEvent Class**: Constants for all event types (STEP_START, STEP_COMPLETE, etc.)
3. **Event-Driven CLI**: No blocking spinners, clean approval handling
4. **Token Tracking**: Per-step and cumulative display
5. **Better Logging**: Agent names shown at startup

### New Pipeline Output Example
```
Pipeline: new_game
Create a new game from concept
Steps: 4

Step 1/4: concept (architect)
  ✓ Complete (2,345 in / 1,234 out, $0.1234)

Step 2/4: architecture (architect)
  ⚠ Approval required for architecture
Proceed? [Y/n]: y
  ✓ Approved
  ✓ Complete (1,567 in / 890 out, $0.0876)

Step 3/4: visual_style (architect)
  ✓ Complete (1,234 in / 567 out, $0.0543)

Step 4/4: initial_mechanics (designer)
  ✓ Complete (987 in / 456 out, $0.0234)

============================================================
✓ Pipeline completed successfully
  Steps: 4/4
  Tokens: 6,133 in / 3,147 out
  Estimated cost: $0.2887
============================================================

Tip: Use gads status to see full outputs
```

---

## Related Files

- `src/gads/cli.py` - CLI implementation (updated)
- `src/gads/orchestrator/core.py` - Pipeline execution (updated)
- `src/gads/orchestrator/__init__.py` - Exports (updated)
- `src/gads/orchestrator/pipeline.py` - Pipeline/step definitions
- `src/gads/agents/base.py` - Agent base class, token tracking

---

## Testing Checklist

- [ ] Run `pytest tests/` to verify no regressions
- [ ] Test `gads pipeline run new_game "space shooter"` with approval prompts
- [ ] Test `gads pipeline run new_game "space shooter" -y` (skip approvals)
- [ ] Test pipeline failure mid-execution to verify completed steps shown
- [ ] Verify token counts match API responses
