import { SearchRequestSchema, SearchResponseSchema, type SearchRequest, type SearchResponse } from '../schemas/search'

const STUB = [
  { id: 'f:readme', kind: 'local_file', title: 'README.md', snippet: 'Local file: project overview + setup steps', source: 'local', trust: 'trusted', score: 0.92 },
  { id: 'e:company:acme', kind: 'entity', title: 'ACME Corp', snippet: 'Entity: example company node (graph-backed)', source: 'kb', trust: 'mixed', score: 0.88 },
  { id: 'w:searx', kind: 'web_doc', title: 'SearxNG documentation', snippet: 'Metasearch backend: instances + settings + engines', source: 'web', trust: 'mixed', score: 0.80 },
  { id: 'c:trusted:science', kind: 'collection', title: '/science (Trusted Collection)', snippet: 'Curated sources + topic constraints + freshness policy', source: 'curation', trust: 'trusted', score: 0.85 },
] as const

export async function search(req: SearchRequest): Promise<SearchResponse> {
  const parsed = SearchRequestSchema.parse(req)
  const q = parsed.q.toLowerCase()

  const modeBoost: Record<string, Record<string, number>> = {
    blended: { local_file: 0.05, entity: 0.05, web_doc: 0.03, collection: 0.04 },
    local:   { local_file: 0.12, entity: 0.02, web_doc: -0.10, collection: -0.05 },
    global:  { local_file: -0.08, entity: 0.06, web_doc: 0.10, collection: 0.08 },
  }

  const results = STUB.map(r => {
    const hit = (r.title + ' ' + (r.snippet ?? '')).toLowerCase()
    const match = hit.includes(q) ? 0.20 : 0.0
    const boost = modeBoost[parsed.mode]?.[r.kind] ?? 0
    const score = Math.max(0, Math.min(1, (r.score ?? 0.5) + match + boost))
    return { ...r, score }
  }).sort((a,b) => (b.score ?? 0) - (a.score ?? 0))

  return SearchResponseSchema.parse({ results, facets: { mode: parsed.mode }, debug: { note: 'stub-search', q: parsed.q, mode: parsed.mode } })
}
