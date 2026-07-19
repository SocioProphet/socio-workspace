# EMVI Focus-State Machine

Status: Draft v0.1

## Purpose

This document defines which surface owns the keyboard at any moment.
Keyboard-first systems fail when focus ownership is ambiguous, so the shell
must distinguish global shell states from local application states.

## Major states

### HOST_IDLE
No EMVI overlay is open. Native host/application ownership applies.

### SHELL_INPUT
The shell overlay is open and accepting grammar input.

### SHELL_RESULTS
The shell owns the result list and local result navigation.

### SHELL_PREVIEW
A preview surface is open under shell control.

### SHELL_ACTION_SHEET
The shell is presenting alternate actions or action details for a selected object.

### LOCAL_LIST_OR_TREE
A local composite widget owns directional navigation.
Examples: sidebar tree, room list, result group.

### EDITOR_INSERT
The editor/composer owns printable input.

### EDITOR_NORMAL
The editor may own modal local navigation and object-level operations.

### TERMINAL_PASSTHROUGH
The terminal or remote shell owns raw input.

### COMPLETION_SURFACE
A completion popup temporarily owns completion keys.

### MODAL_CONFIRMATION
A confirmation dialog owns local navigation and confirmation/cancel.

### PLAN_REVIEW
A structured execution plan is being inspected before confirmation.

### TOOL_CONFIRMATION
A tool-specific confirmation surface is active.

## Ownership rules

### Printable input
Belongs to the local surface in pass-through states.
EMVI must not steal raw text input from:
- editor insert mode
- browser text fields
- terminal pass-through
- password/sensitive fields
- accessibility-owned surfaces

### Tab
- Completion popup owns Tab first.
- If no completion popup is active, Tab/Shift-Tab move between regions or controls.
- Tab should not silently trigger shell interpretation while local completion is active.

### Arrow keys
- Arrows navigate within local composite regions.
- In shell-owned results, arrows move across results.
- In editor/terminal pass-through, local surface rules apply.

### Up/Down boundary gating
In multiline text surfaces, Up/Down may escape into history or retargeting only when:
- caret is at the first/last boundary
- no conflicting selection is active
- the local surface opts into history behavior

### Escape
Escape unwinds the innermost active transient state first:
1. completion popup
2. modal/tool confirmation
3. preview/action sheet
4. shell overlay
Then native host/application ownership resumes.

### Enter
Enter is not a universal commit key.
- In composition surfaces it may remain newline.
- In result lists it may activate the default action.
- In review/confirmation states it may accept the current action only when clearly owned there.

## Transition rules

- HOST_IDLE -> SHELL_INPUT requires explicit summon.
- SHELL_INPUT -> SHELL_RESULTS when results resolve.
- SHELL_RESULTS -> SHELL_PREVIEW when preview opens.
- Any shell execution path -> PLAN_REVIEW when an ActionSpec requires explicit review.
- PLAN_REVIEW -> TOOL_CONFIRMATION when a tool-specific confirmation boundary is required.
- TOOL_CONFIRMATION -> prior state on cancel.
- Any shell state -> HOST_IDLE on full dismiss.

## Invariants

1. Grammar only runs in grammar-owning states.
2. Local modal/editor/terminal ownership takes priority over global shell parsing.
3. Completion surfaces own completion keys first.
4. Focus owner must be visually or structurally inspectable.
5. Every dismiss path must be reversible and legible.
