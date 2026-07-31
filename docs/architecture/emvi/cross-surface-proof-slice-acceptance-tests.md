# Cross-Surface Proof Slice Acceptance Tests

Status: Draft v0.1

## Acceptance target

The proof slice passes when one operator can coordinate browser, editor,
terminal, graph, collection, and provenance flows under one shell without
breaking host-boundary rules.

## Test set

### A. Focus correctness
- [ ] Shell grammar does not activate in editor insert mode.
- [ ] Shell grammar does not activate in terminal pass-through.
- [ ] Escape unwinds the innermost transient state first.
- [ ] Completion surface owns Tab when active.

### B. Browser / page capture
- [ ] A page can be opened through the local UI runtime.
- [ ] Current page can be captured into a collection.
- [ ] Captured page item can be previewed later.

### C. Editor / snippet capture
- [ ] A selected file range can be captured into the active collection.
- [ ] Captured snippet retains locator and anchor data.

### D. Guarded shell execution
- [ ] A shell command is represented as an ActionSpec before execution.
- [ ] Policy can deny, allow, or require confirmation.
- [ ] Captured output is stored as a typed object.

### E. Graph capture
- [ ] A graph query can be executed through the graph façade.
- [ ] At least one graph result can be appended to the collection.

### F. Snapshot and export
- [ ] The working collection can be frozen into a snapshot.
- [ ] The snapshot can be exported to a portable form.

### G. Provenance and ledger
- [ ] Every step emits inspectable provenance.
- [ ] The operator can inspect what was captured and what executed.

## Failure conditions

The proof slice fails if any of the following occur:
- grammar steals local input ownership
- capture loses locator/anchor data
- execution bypasses policy/confirmation requirements
- export requires the live shell to be useful
- provenance is missing for a nontrivial action
