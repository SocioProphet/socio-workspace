import {
  OperationSchema,
  OperationListResponseSchema,
  type Operation,
  type OperationListResponse,
  type OperationSearchRequest,
} from '../schemas/operation'

// ── Stub data ──────────────────────────────────────────────────────────────

const STUB_OPERATIONS: Operation[] = [
  OperationSchema.parse({
    id: 'op-001',
    type: 'upload/import',
    stage: 'running',
    title: 'Import dataset: sales-q1-2026.csv',
    actor: 'user:alice',
    createdAt: '2026-05-06T18:00:00Z',
    updatedAt: '2026-05-06T18:05:00Z',
    detail: 'Parsing and validating rows. 840 / 1200 complete.',
    policyBlock: null,
    decisions: [],
    errors: [],
    artifacts: [
      { id: 'art-001', kind: 'dataset', label: 'sales-q1-2026.csv', source: 'local-upload', admissionStatus: 'pending', operationHistory: ['op-001'] },
    ],
    events: [
      { eventId: 'ev-001-a', operationId: 'op-001', ts: '2026-05-06T18:00:00Z', stage: 'pending', detail: 'Queued for processing' },
      { eventId: 'ev-001-b', operationId: 'op-001', ts: '2026-05-06T18:00:05Z', stage: 'running', detail: 'Started row parsing' },
    ],
  }),
  OperationSchema.parse({
    id: 'op-002',
    type: 'agent-patch/report',
    stage: 'waiting-decision',
    title: 'Agent patch: update entity graph (agent:hal-9)',
    actor: 'agent:hal-9',
    createdAt: '2026-05-06T17:30:00Z',
    updatedAt: '2026-05-06T17:45:00Z',
    detail: 'Agent proposes 14 graph mutations. Human review required before activation.',
    policyBlock: null,
    decisions: [
      {
        id: 'dec-002-a',
        type: 'agent-artifact-admission',
        prompt: 'Agent hal-9 proposes 14 entity mutations. Admit to workspace?',
        responsibleActor: 'user:operator',
        options: [
          { id: 'admit', label: 'Admit all', description: 'Accept all proposed mutations', destructive: false },
          { id: 'reject', label: 'Reject', description: 'Discard agent changes', destructive: false },
          { id: 'review', label: 'Review individually', description: 'Open per-mutation review', destructive: false },
        ],
        chosenOptionId: null,
        resolvedAt: null,
      },
    ],
    errors: [],
    artifacts: [
      { id: 'art-002', kind: 'graph-patch', label: 'hal-9/patch-2026-05-06', source: 'agent:hal-9', admissionStatus: 'review', operationHistory: ['op-002'] },
    ],
    events: [
      { eventId: 'ev-002-a', operationId: 'op-002', ts: '2026-05-06T17:30:00Z', stage: 'pending', detail: 'Agent patch queued' },
      { eventId: 'ev-002-b', operationId: 'op-002', ts: '2026-05-06T17:45:00Z', stage: 'waiting-decision', detail: 'Awaiting operator decision' },
    ],
  }),
  OperationSchema.parse({
    id: 'op-003',
    type: 'memory-ingestion',
    stage: 'blocked',
    title: 'Ingest memory: session-2026-05-05.jsonl',
    actor: 'user:bob',
    createdAt: '2026-05-06T16:00:00Z',
    updatedAt: '2026-05-06T16:10:00Z',
    detail: 'Policy block: memory ingestion requires data-classification tag.',
    policyBlock: {
      policyId: 'policy:memory-classification-required',
      reason: 'All ingested memory must carry a data-classification tag before workspace admission.',
      responsibleActor: 'user:bob',
      remediationOptions: [
        'Add classification tag to source file and re-submit.',
        'Request policy exemption from workspace administrator.',
      ],
    },
    decisions: [],
    errors: [],
    artifacts: [],
    events: [
      { eventId: 'ev-003-a', operationId: 'op-003', ts: '2026-05-06T16:00:00Z', stage: 'pending' },
      { eventId: 'ev-003-b', operationId: 'op-003', ts: '2026-05-06T16:10:00Z', stage: 'blocked', detail: 'Policy: memory-classification-required' },
    ],
  }),
  OperationSchema.parse({
    id: 'op-004',
    type: 'repo-import/index',
    stage: 'completed',
    title: 'Index repo: github.com/example/analytics',
    actor: 'user:alice',
    createdAt: '2026-05-06T14:00:00Z',
    updatedAt: '2026-05-06T14:30:00Z',
    detail: 'Repository indexed successfully. 3,208 files processed.',
    policyBlock: null,
    decisions: [],
    errors: [],
    artifacts: [
      { id: 'art-004', kind: 'repo-index', label: 'example/analytics@main', source: 'github', admissionStatus: 'admitted', operationHistory: ['op-004'] },
    ],
    events: [
      { eventId: 'ev-004-a', operationId: 'op-004', ts: '2026-05-06T14:00:00Z', stage: 'pending' },
      { eventId: 'ev-004-b', operationId: 'op-004', ts: '2026-05-06T14:01:00Z', stage: 'running', detail: 'Cloning repository' },
      { eventId: 'ev-004-c', operationId: 'op-004', ts: '2026-05-06T14:30:00Z', stage: 'completed', detail: 'Index complete' },
    ],
  }),
  OperationSchema.parse({
    id: 'op-005',
    type: 'terminal-command',
    stage: 'failed',
    title: 'Terminal: npm run build (workspace-ui)',
    actor: 'user:alice',
    createdAt: '2026-05-06T13:00:00Z',
    updatedAt: '2026-05-06T13:02:00Z',
    policyBlock: null,
    decisions: [],
    errors: [
      {
        code: 'BUILD_FAILED',
        message: 'TypeScript compilation error in src/index.ts (line 42). Redacted diagnostics available.',
        responsibleActor: 'user:alice',
        safeNextAction: 'Fix TypeScript error and re-run build.',
        redacted: true,
      },
    ],
    artifacts: [],
    events: [
      { eventId: 'ev-005-a', operationId: 'op-005', ts: '2026-05-06T13:00:00Z', stage: 'pending' },
      { eventId: 'ev-005-b', operationId: 'op-005', ts: '2026-05-06T13:00:05Z', stage: 'running', detail: 'Running npm run build' },
      { eventId: 'ev-005-c', operationId: 'op-005', ts: '2026-05-06T13:02:00Z', stage: 'failed', detail: 'BUILD_FAILED' },
    ],
  }),
]

// ── API functions ──────────────────────────────────────────────────────────

export async function listOperations(req?: Partial<OperationSearchRequest>): Promise<OperationListResponse> {
  let ops = [...STUB_OPERATIONS]

  if (req?.q) {
    const q = req.q.toLowerCase()
    ops = ops.filter(o =>
      o.title.toLowerCase().includes(q) ||
      o.actor.toLowerCase().includes(q) ||
      (o.detail ?? '').toLowerCase().includes(q)
    )
  }
  if (req?.stage) ops = ops.filter(o => o.stage === req.stage)
  if (req?.type) ops = ops.filter(o => o.type === req.type)
  if (req?.actor) ops = ops.filter(o => o.actor === req.actor)

  return OperationListResponseSchema.parse({ operations: ops, total: ops.length })
}

export async function getOperation(id: string): Promise<Operation | null> {
  return STUB_OPERATIONS.find(o => o.id === id) ?? null
}

// Re-export request type so callers don't need a separate import
export type { OperationSearchRequest }
