# Patent Design-Around Notes

Status: scaffold.

This file records high-level design-around doctrine for patent-sensitive areas.

## Core rules

- Patents are boundary signals, not implementation recipes.
- Never copy claims or proprietary implementation details into repo issues.
- Prefer independently derived open implementations.
- Separate benchmark reuse from product implementation.
- Maintain explicit legal-review queues for high-risk areas.

## Current high-risk clusters

### Cyc commonsense and inference

Risk:
- ontology structure
- inference-control concepts
- proprietary assertion organization
- historical licensing restrictions

Allowed use:
- conceptual reference
- architectural lessons
- public-paper citation

Blocked until review:
- direct ontology reuse
- proprietary assertion export
- claim-derived implementation

### IBM causal extraction and semantic integration

Risk:
- enterprise semantic integration workflows
- entity linking
- semantic linkage
- causal extraction productization

Allowed use:
- benchmark comparison
- conceptual lineage
- independently implemented graph structures

Blocked until review:
- claim-level workflow copying
- proprietary pipeline duplication

### Watson/DeepQA architecture

Risk:
- pipeline patents
- answer scoring/productization methods
- enterprise QA implementation details

Allowed use:
- architectural study
- evidence-ranking doctrine
- provenance and confidence concepts

Blocked until review:
- direct reproduction of patented workflows
- proprietary data-flow cloning

## Required future additions

- patent family IDs
- filing/publication dates
- active vs expired status
- assignees
- claim-category summaries
- legal-review owner
- component risk matrix
