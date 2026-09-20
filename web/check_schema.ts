import { FIXTURES } from './fixtures/analysis-states';
import { AnalysisResultSchema } from './schemas/analysis';

console.log(JSON.stringify(AnalysisResultSchema.safeParse(FIXTURES.review_recommended), null, 2));
