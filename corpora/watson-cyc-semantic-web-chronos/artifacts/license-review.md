# Artifact License Review

Status: scaffold.

This file tracks artifact reuse boundaries.

## Rules

- No artifact is reusable until license and access status are verified.
- Proprietary IBM or Cycorp systems are conceptual references by default.
- Patent-heavy areas require design-around notes.
- Benchmark reuse and implementation reuse are separate categories.

## Current review queue

| Artifact | Current status | Risk | Notes |
|---|---|---|---|
| CHRONOS | unknown | medium | system lineage known, artifact/license unknown |
| ULKB Logic | unknown | medium | framework/code lineage needs audit |
| WikiCausal | unknown | low-medium | dataset availability and license pending |
| KG2Tables | public artifact identified | low | benchmark/reference likely reusable, confirm license |
| tBiodiv | public artifact identified | low | verify dataset license/version |
| TabSketchFM | unknown | medium | code/model availability pending |
| TOPJoin | unknown | medium | workshop/arXiv lineage identified; artifact status pending |
| Watson/DeepQA public materials | restricted/unknown | high | architecture reference only until rights clarified |
| Cyc acquisition materials | restricted/unknown | high | conceptual reference only pending rights review |

## Planned fields

- artifact_id
- source_url
- license
- access_status
- reuse_mode
- derivative_work_risk
- patent_overlap
- required_attribution
- review_owner
- review_date
