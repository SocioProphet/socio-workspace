# EMVI Agent Stack Teaching Guide

Status: Draft v0.1

## One-sentence model

EMVI is the keyboard-first operator shell over a local-first, offline-first,
auditable agent stack.

## How to explain the layers

### EMVI shell layer
What the operator sees and uses:
- summon
- focus
- grammar
- preview
- capture
- plan review
- confirmation

### Agent stack layer
What actually executes or decides:
- planner proposes larger decompositions
- policy evaluates permissions and trust requirements
- graph/knowledge services hold or query structured truth
- UI runtime renders local digital-twin views
- shell service runs guarded commands
- collection service manages working sets and snapshots
- ledger records provenance and execution visibility
- placement decides host/LMS/fog/cloud execution locality

## Teaching examples

### Example 1: capture a page into research
1. open a page through local UI runtime
2. capture current page into a collection
3. inspect the resulting collection member
4. confirm provenance exists

### Example 2: capture a snippet and relate it to a page
1. select a snippet in an editor
2. capture selection into the same collection
3. add an annotation linking the snippet and page
4. freeze a snapshot for handoff

### Example 3: guarded shell execution
1. propose a shell action
2. review the ActionSpec
3. allow or deny through policy
4. capture output and ledger trail

## Key teaching points

- Parsing is not execution.
- Search is the default.
- Slash is scope in shell-owned states.
- Collections are mutable working sets.
- Snapshots are immutable evidence/handoff objects.
- Host and local surface ownership still matter.

## Common mistakes to correct

- treating EMVI as the planner
- treating browser work as direct remote-web trust
- treating a locator as an anchor
- treating every shortcut as globally owned by the shell
- treating collections as simple bookmark piles instead of typed working sets
