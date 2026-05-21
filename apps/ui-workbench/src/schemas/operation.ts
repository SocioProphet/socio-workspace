import { z } from 'zod'

// ── Operation type taxonomy ────────────────────────────────────────────────
export const OperationTypeSchema = z.enum([
  'upload/import',
  'agent-patch/report',
  'memory-ingestion',
  'terminal-command',
  'browser-capture/download',
  'repo-import/index',
])
export type OperationType = z.infer<typeof OperationTypeSchema>

// ── Operation stage ────────────────────────────────────────────────────────
export const OperationStageSchema = z.enum([
  'pending',
  'running',
  'waiting-decision',
  'blocked',
  'completed',
  'cancelled',
  'failed',
])
export type OperationStage = z.infer<typeof OperationStageSchema>

// ── Decision types ─────────────────────────────────────────────────────────
export const DecisionTypeSchema = z.enum([
  'conflict-resolution',
  'metadata-requirement',
  'policy-override',
  'agent-artifact-admission',
  'destructive-cancel',
])
export type DecisionType = z.infer<typeof DecisionTypeSchema>

export const DecisionOptionSchema = z.object({
  id: z.string(),
  label: z.string(),
  description: z.string().optional(),
  destructive: z.boolean().default(false),
})
export type DecisionOption = z.infer<typeof DecisionOptionSchema>

export const DecisionCardSchema = z.object({
  id: z.string(),
  type: DecisionTypeSchema,
  prompt: z.string(),
  responsibleActor: z.string(),
  options: z.array(DecisionOptionSchema).min(1),
  chosenOptionId: z.string().nullable().default(null),
  resolvedAt: z.string().nullable().default(null),
})
export type DecisionCard = z.infer<typeof DecisionCardSchema>

// ── Policy block ───────────────────────────────────────────────────────────
export const PolicyBlockSchema = z.object({
  policyId: z.string(),
  reason: z.string(),
  responsibleActor: z.string(),
  remediationOptions: z.array(z.string()).default([]),
})
export type PolicyBlock = z.infer<typeof PolicyBlockSchema>

// ── Error detail ───────────────────────────────────────────────────────────
export const OperationErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  responsibleActor: z.string().optional(),
  safeNextAction: z.string().optional(),
  redacted: z.boolean().default(true),
})
export type OperationError = z.infer<typeof OperationErrorSchema>

// ── Artifact ───────────────────────────────────────────────────────────────
export const ArtifactSchema = z.object({
  id: z.string(),
  kind: z.string(),
  label: z.string(),
  source: z.string().optional(),
  admissionStatus: z.enum(['pending', 'admitted', 'rejected', 'review']).default('pending'),
  operationHistory: z.array(z.string()).default([]),
})
export type Artifact = z.infer<typeof ArtifactSchema>

// ── Operation event (snapshot-driven) ─────────────────────────────────────
export const OperationEventSchema = z.object({
  eventId: z.string(),
  operationId: z.string(),
  ts: z.string(),
  stage: OperationStageSchema,
  detail: z.string().optional(),
})
export type OperationEvent = z.infer<typeof OperationEventSchema>

// ── Operation (full record) ────────────────────────────────────────────────
export const OperationSchema = z.object({
  id: z.string(),
  type: OperationTypeSchema,
  stage: OperationStageSchema,
  title: z.string(),
  actor: z.string(),
  createdAt: z.string(),
  updatedAt: z.string(),
  detail: z.string().optional(),
  policyBlock: PolicyBlockSchema.nullable().default(null),
  decisions: z.array(DecisionCardSchema).default([]),
  errors: z.array(OperationErrorSchema).default([]),
  artifacts: z.array(ArtifactSchema).default([]),
  events: z.array(OperationEventSchema).default([]),
})
export type Operation = z.infer<typeof OperationSchema>

// ── List response ──────────────────────────────────────────────────────────
export const OperationListResponseSchema = z.object({
  operations: z.array(OperationSchema),
  total: z.number().int().min(0),
})
export type OperationListResponse = z.infer<typeof OperationListResponseSchema>

// ── Search request ─────────────────────────────────────────────────────────
export const OperationSearchRequestSchema = z.object({
  q: z.string().default(''),
  stage: OperationStageSchema.optional(),
  type: OperationTypeSchema.optional(),
  actor: z.string().optional(),
  page: z.number().int().min(1).default(1),
})
export type OperationSearchRequest = z.infer<typeof OperationSearchRequestSchema>
