# Regulated AI control-plane benchmark v0

Status: draft
Owner: Sociosphere governance layer
Date: 2026-06-05

## Purpose

This benchmark captures visible product patterns from regulated AI systems and maps them into SocioProphet's open governance model. The goal is capability coverage with stronger transparency, provenance, replayability, authority boundaries, and validator-backed claims.

This document is a design benchmark. It is not a claim that SocioProphet implements every runtime capability listed here.

## Source set

| Source | URL | Use |
|---|---|---|
| OpenAI Business | https://openai.com/business/ | Enterprise/product/security capability baseline |
| ChatGPT Enterprise | https://chatgpt.com/business/enterprise/ | Enterprise agents, app/data connectors, security, deployment support |
| Harvey platform | https://www.harvey.ai/ | Legal/professional-services product surface baseline |
| Harvey security | https://www.harvey.ai/security | Legal AI security and enterprise-control baseline |
| Ambience Healthcare | https://www.ambiencehealthcare.com/ | Healthcare documentation/coding/productivity baseline |
| HealthBench paper | https://arxiv.org/abs/2505.08775 | Open rubric-driven medical evaluation baseline |
| HealthBench Professional paper | https://arxiv.org/abs/2604.27470 | Clinician-task evaluation baseline |

## Competitor/product patterns captured

### OpenAI enterprise pattern

OpenAI's business page presents ChatGPT for Business/Enterprise as a workforce AI layer with advanced models, tools, specialized agents, app integrations, enterprise security, admin controls, SAML SSO, and compliance claims. It explicitly mentions workspace agents that can run shared workflows, handle recurring tasks, and work across team tools. It also identifies integrations with company data sources such as Google Drive, SharePoint, GitHub, Dropbox, Box, and related apps, plus Codex and ChatGPT agent usage.

SocioProphet mapping:

- Workspace agents become governed `ProcedureTemplate` plus `InstitutionalAction` records.
- App integrations become `ConnectorContract`, `SourcePermission`, and `AppActionPolicy` objects.
- Enterprise admin controls become `Actor`, `Role`, `AuthorityBoundary`, and `CapabilityGrant` graph state.
- Data privacy/security claims become `SecurityProfile`, `RetentionPolicy`, `ComplianceLogEvent`, and `ExecutionReceipt` objects.
- Agent outputs require `EvidenceBundle`, approval posture, graph snapshot, and replay references before high-stakes use.

### Harvey legal/professional-services pattern

Harvey presents a unified legal/professional-services platform with Assistant, Vault, Knowledge, Agents, Ecosystem, Contract Intelligence, Command Center, and Shared Spaces surfaces. Its platform language includes asking questions, analyzing documents, drafting, securely storing and bulk-analyzing legal documents, legal/regulatory/tax research, end-to-end purpose-built agents, ecosystem access, source grounding, analytics, benchmarking, and secure shared collaboration.

Harvey's security page identifies no-model-training commitments, SAML SSO, audit logs, IP allow-listing, data lifecycle management, contractual controls aligned with SOC 2, ISO, GDPR and other standards, independent testing, encryption in transit and at rest, role-based access controls, logical workspace separation, and regional processing options.

SocioProphet mapping:

- Legal assistant capabilities become human-in-command synthesis workflows with citation-first `EvidenceBundle` objects.
- Vault/document review becomes evidence-vault workflow: `ExtractionReceipt`, `ReviewTable`, `RedactionPolicy`, `GraphSnapshot`.
- Legal knowledge grounding becomes a source-authority and jurisdiction-aware knowledge registry.
- Workflow agents become versioned `ProcedureTemplate` objects with approval gates and replay tests.
- Security controls become machine-readable policies and receipts, not only vendor assertions.

### Ambience healthcare pattern

Ambience presents a healthcare AI platform for clinical documentation and coding, with published product claims around utilization, charting-time reduction, documentation quality, revenue integrity, compliance, real-time code suggestions, risk reduction, and specialty adaptation. The site states that the product adapts to workflows, documentation, and coding across 200+ specialties.

SocioProphet mapping:

- Clinical documentation becomes domain-specific `ProcedureTemplate` workflows with clinician approval gates.
- Coding/revenue integrity becomes `PolicyBasis`, coding-rule evidence, and execution receipts.
- Specialty adaptation becomes domain packs with explicit source authority, policy basis, and benchmark coverage.
- Utilization/time-saved claims become `WorkflowBench` metrics with transparent adoption, correction, override, and quality dimensions.
- Compliance/risk claims become retained evidence, graph snapshots, and release/admission validators.

### HealthBench evaluation pattern

HealthBench defines an open health-model benchmark using 5,000 multi-turn conversations and physician-created rubrics. HealthBench Professional extends this evaluation posture to real clinician ChatGPT tasks, organized around care consult, writing/documentation, and medical research, with physician-written conversations and rubric adjudication.

SocioProphet mapping:

- Domain evaluations become `DomainBench` objects.
- Workflow evaluations become `WorkflowBench` objects.
- Governance and authority checks become `GovernanceBench` objects.
- Replay and evidence retention checks become `ReplayBench` objects.
- Rubrics must carry source lineage, domain owner, adjudication method, fixture coverage, and versioned result records.

## Parity-plus governance bar

Every captured capability must be upgraded into a governed SocioProphet primitive before it becomes a product claim:

1. Actor, role, authority boundary, policy basis, and capability grant are explicit.
2. Evidence bundle includes provenance, source authority class, content digest, and contradiction hooks.
3. Human-in-command separation exists between synthesis, recommendation, approval, override, and execution.
4. Execution receipt includes artifact refs, graph snapshot refs, replay posture, and determinism class.
5. Connector actions are classified by read/write/action risk and retain source-system permission posture.
6. Benchmarks expose rubric lineage, task coverage, pass/fail thresholds, failure classes, and replayable scoring.
7. Runtime claims require schemas, fixtures, validators, graph queries, and release-readiness admission.

## Immediate schema backlog

| Object | Reason |
|---|---|
| `GovernanceBench` | Test authority, policy, approval, override, and audit behavior. |
| `WorkflowBench` | Test operational workflow quality, adoption, timing, correction, and override metrics. |
| `DomainBench` | Test domain-specific rubrics, task coverage, and expert adjudication. |
| `ReplayBench` | Test replayability, graph snapshot availability, and evidence retention. |
| `ConnectorContract` | Represent external data/tool connectors, scopes, and permission inheritance. |
| `CapabilityGrant` | Bind actors/roles to allowed tool, app, or agent capabilities. |
| `AppActionPolicy` | Classify app/plugin actions and enforce confirmation/approval rules. |
| `SecurityProfile` | Capture identity, region, retention, encryption, audit, and contractual controls. |
| `ExtractionReceipt` | Prove document/data extraction lineage and review-table provenance. |
| `GraphSnapshot` | Pin graph state used by action, benchmark, release, or review decisions. |
| `ComplianceLogEvent` | Represent retained compliance/audit events and export posture. |
| `RetentionPolicy` | Represent retention, deletion, export, and legal-hold posture. |

## Boundary

This benchmark records product-pattern requirements. It does not claim implementation completeness, medical/legal fitness, production certification, or competitive equivalence. Downstream work must add schema stubs, fixtures, validators, HellGraph query fixtures, AgentPlane receipts, and Prophet Platform admission tests before product-readiness claims are allowed.
