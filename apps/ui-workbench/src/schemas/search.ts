import { z } from 'zod'

export const SearchModeSchema = z.enum(['blended','local','global'])
export type SearchMode = z.infer<typeof SearchModeSchema>

export const SearchRequestSchema = z.object({
  q: z.string().min(1),
  mode: SearchModeSchema.default('blended'),
  filters: z.record(z.string(), z.any()).optional(),
  page: z.number().int().min(1).default(1),
})

export const SearchResultSchema = z.object({
  id: z.string(),
  kind: z.enum(['local_file','web_doc','entity','collection']),
  title: z.string(),
  snippet: z.string().optional(),
  source: z.string().optional(),
  trust: z.enum(['trusted','mixed','untrusted']).default('mixed'),
  score: z.number().optional(),
  href: z.string().optional(),
})

export const SearchResponseSchema = z.object({
  results: z.array(SearchResultSchema),
  facets: z.record(z.string(), z.any()).default({}),
  debug: z.record(z.string(), z.any()).optional(),
})

export type SearchRequest = z.infer<typeof SearchRequestSchema>
export type SearchResponse = z.infer<typeof SearchResponseSchema>
export type SearchResult = z.infer<typeof SearchResultSchema>
