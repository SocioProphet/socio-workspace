import { defineStore } from 'pinia'
import type { Operation } from '../schemas/operation'

export const useOperationStore = defineStore('operation', {
  state: () => ({
    operations: [] as Operation[],
    selectedId: null as string | null,
    inspectorOpen: false,
  }),
  getters: {
    active(state): Operation[] {
      return state.operations.filter(
        o => o.stage === 'running' || o.stage === 'waiting-decision' || o.stage === 'pending' || o.stage === 'blocked'
      )
    },
    selected(state): Operation | null {
      return state.operations.find(o => o.id === state.selectedId) ?? null
    },
  },
  actions: {
    load(ops: Operation[]) {
      this.operations = ops
    },
    upsert(op: Operation) {
      const idx = this.operations.findIndex(o => o.id === op.id)
      if (idx >= 0) this.operations[idx] = op
      else this.operations.push(op)
    },
    select(id: string | null) {
      this.selectedId = id
      this.inspectorOpen = id !== null
    },
    closeInspector() {
      this.inspectorOpen = false
      this.selectedId = null
    },
    resolveDecision(operationId: string, decisionId: string, optionId: string) {
      const op = this.operations.find(o => o.id === operationId)
      if (!op) return
      const decIdx = op.decisions.findIndex(d => d.id === decisionId)
      if (decIdx < 0) return
      const dec = op.decisions[decIdx]
      if (!dec) return
      dec.chosenOptionId = optionId
      dec.resolvedAt = new Date().toISOString()
    },
  },
})
