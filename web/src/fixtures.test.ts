import { describe, it, expect } from 'vitest';
import { FIXTURES } from './fixtures/analysis-states';
import { AnalysisResultSchema } from './schemas/analysis';

describe('Contract Fixtures', () => {
  it('validates success fixture against schema', () => {
    const result = AnalysisResultSchema.safeParse(FIXTURES.success);
    expect(result.success).toBe(true);
  });
  
  it('validates review_recommended fixture against schema', () => {
    const result = AnalysisResultSchema.safeParse(FIXTURES.review_recommended);
    expect(result.success).toBe(true);
  });
});
