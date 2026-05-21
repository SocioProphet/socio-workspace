# Cognitive Architecture Map

Status: v0.1 corpus architecture mapping.

This file maps external cognitive-architecture literature to SocioProphet roles. These systems are references and design patterns, not monolithic platform choices.

## ACT-R

Use for Alexandrian Academy and HolographMe.

Relevant pattern: declarative chunks, procedural productions, buffers, activation, retrieval latency, utility learning, human timing, and skill acquisition.

SocioProphet use: cognitive tutoring, operator workload, human digital twin behavior, task-learning traces, learning-progress models.

Do not use as the primary autonomous infrastructure runtime.

## Soar

Use for Holmes deliberation tier.

Relevant pattern: working memory, operator proposal/application, impasses, subgoals, semantic memory, episodic memory, and chunking.

SocioProphet use: plan repair, explicit deliberation, KGQA escalation, proof-search framing, causal reasoning, explanation chains.

Risk: rule explosion, unbounded deliberation, overgeneralized chunks.

Control: reasoning budgets, impasse thresholds, proof-cost estimates, chunk review.

## LIDA

Use for Sociosphere attention and broadcast.

Relevant pattern: competing coalitions, attention selection, global broadcast, cognitive cycle.

SocioProphet use: slash-topic attention surface, policy-warning broadcast, evidence-gap broadcast, issue/release routing, operational salience.

Risk: salience bottleneck and noisy global broadcast.

Control: typed events, priority channels, source-quality metadata, rate limits, and audit trails.

## CLARION

Use for Agentplane / Policy Fabric implicit-explicit bridge.

Relevant pattern: implicit learned behavior plus explicit rule knowledge.

SocioProphet use: learned agent proposals require explicit policy approval; trait drift is measured separately from authorization.

Risk: implicit behavior diverges from explicit explanation.

Control: two-key safety, drift checks, explicit rule gates, intervention audit records.

## Sigma

Use for Holmes uncertainty-aware inference coprocessor.

Relevant pattern: factor graphs, message passing, mixed symbolic/probabilistic reasoning.

SocioProphet use: uncertain event claims, causal KG edge confidence, noisy telemetry, probabilistic KGQA evidence.

Risk: expensive inference and hard-to-debug belief state.

Control: reasoning budgets, trace output, confidence calibration, and policy thresholds.

## OpenCog / Hyperon

Use as graph-native inspiration and cautionary reference.

Relevant pattern: metagraph knowledge representation, heterogeneous reasoning, program-as-graph representation, MeTTa/Atomspace-style rewriting.

SocioProphet use: staged graph-native reasoning experiments and ontology/reasoning research.

Risk: integrative sprawl, self-modification, uncontrolled graph mutation, unsafe actuator coupling.

Control: sandboxing, read-only default, staged writes, reviewable mutations, external Policy Fabric enforcement.

## ICARUS

Use for Agentplane skill-library and skill-promotion patterns.

SocioProphet use: promote successful traces into reviewed skills with provenance and validation.

Risk: brittle skill libraries.

Control: skill versioning, provenance, regression tests, rollback.

## EPIC

Use for HolographMe and Alexandrian Academy.

SocioProphet use: human perceptual/cognitive/motor timing and interface workload modeling.

Do not use as autonomous runtime.

## CHREST

Use for Sherlock/Holmes expert chunk recognition.

SocioProphet use: bounded-domain template recognition and expertise modeling.

Risk: template brittleness.

Control: provenance-bound templates and evidence-backed activation.

## Leabra

Use only in perception or skill modules.

SocioProphet use: neural learning reference for low-level perception/skill acquisition.

Risk: subsymbolic opacity and action authorization confusion.

Control: no high-risk authorization from learned outputs alone.

## HTM

Use for SourceOS telemetry and anomaly detection only as a secondary reference.

SocioProphet use: streaming anomaly detection, sequence prediction, telemetry surprise signals.

Risk: false positives and weak semantic grounding.

Control: anomaly-to-evidence escalation only; no direct destructive action.

## BICA / Common Model

Use as architecture-completeness checklist.

SocioProphet use: verify that working memory, procedural control, declarative/procedural stores, perceptual/action loops, learning hooks, and cognitive cycles are accounted for.

Do not use as an implementation prescription.
