import { defineStore } from 'pinia'
export type SearchMode = 'blended' | 'local' | 'global'

export const useSearchStore = defineStore('search', {
  state: () => ({ recentQueries: [] as string[], mode: 'blended' as SearchMode }),
  actions: {
    pushRecent(q: string) {
      const s = q.trim(); if (!s) return
      this.recentQueries = [s, ...this.recentQueries.filter(x => x !== s)].slice(0, 20)
    },
    setMode(m: SearchMode) { this.mode = m },
  },
})
