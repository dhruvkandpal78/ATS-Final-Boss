import { z } from 'zod';

export const ModuleResultSchema = z.object({
  status: z.enum(['ok', 'not_applicable', 'unsupported', 'error']),
  score: z.number().nullable(),
  reason: z.string().nullable().optional(),
  findings: z.array(z.any()).optional()
});

export const FindingSchema = z.object({
  id: z.string(),
  detector: z.string(),
  category: z.string(),
  severity: z.string(),
  explanation: z.string(),
  anchor: z.any().optional()
});

export const AnalysisResultSchema = z.object({
  schema_version: z.literal('2.0'),
  analysis_id: z.string(),
  created_at: z.string(), // ISO8601
  status: z.enum(['complete', 'partial', 'unscorable']),
  input_mode: z.enum(['text', 'pdf']),
  model: z.object({
    id: z.string().nullable(),
    calibrated: z.boolean()
  }),
  policy_version: z.string(),
  score: z.number().nullable(),
  score_kind: z.enum(['calibrated_probability', 'model_score', 'unavailable']),
  decision: z.enum(['no_signals_detected', 'review_recommended', 'insufficient_evidence']),
  reason_codes: z.array(z.string()),
  coverage: z.object({
    pages_total: z.number().nullable(),
    pages_analyzed: z.number().nullable(),
    limitations: z.array(z.string())
  }),
  modules: z.object({
    a: ModuleResultSchema,
    b: ModuleResultSchema,
    c: ModuleResultSchema
  }),
  findings: z.array(FindingSchema),
  timings_ms: z.record(z.number())
});

export type AnalysisResult = z.infer<typeof AnalysisResultSchema>;
