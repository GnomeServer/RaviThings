# Command Console Upgrade — Approved Design
Date: 2026-04-02

## Goal
Transform the OSINT Atlas command console from a read-only query terminal into a full command center with action commands, multi-step reasoning, spatial intelligence, session memory, and intent inference.

## Three Levels

### Level 1: Action Commands
6 new MAP_CMD actions: research, kill_chain, assess, compare, export_csv, radius. Each calls existing frontend functions or adds focused new ones. Progress streams inline in chat.

### Level 2: Multi-Step Reasoning
LLM plans multi-step analysis, executes commands one at a time, receives feedback (filter counts, matched contractors), continues to next step. Powered by enhanced session context sent with each query.

### Level 3: Spatial + Session Memory
- Radius queries with haversine distance, Leaflet circle overlays
- Session state tracking: active filters, selected contractor, recent references
- Context compression for follow-up queries ("those", "that contractor")

### Intent Inference
LLM infers actions from natural language. "dig into Sandia" → research + open_panel. "how would you attack ORNL" → kill_chain. When uncertain, announces before executing.

## Files Modified
- `test_atlas_server.py` — Enhanced system prompt
- `frontend/static/contractor-map.html` — Extended MAP_CMD dispatcher, action handlers, session state, radius math, compare renderer, export, step feedback

## System Prompt Additions
- New command documentation (6 action types)
- Intent inference rules with examples
- Session context format (active_filter, visible_count, selected_contractor)
- Multi-step analysis guidelines
- "Suggest before executing" rule for long-running actions
