import React, { useState } from 'react';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { FindingsList } from '../components/FindingsList';

const SCENARIOS = [
  { id: 'baseline', name: 'Baseline (No Attack)' },
  { id: 'keyword_stuffing', name: 'Keyword Stuffing (Type A)' },
  { id: 'prompt_injection', name: 'Prompt Injection (Type D)' },
  { id: 'structural_hidden', name: 'Structural Hidden Text (Type B)' },
];

export default function LabPage() {
  const [selectedScenario, setSelectedScenario] = useState(SCENARIOS[0].id);

  // Hardcoded pre-calculated artifacts for U08
  const getResults = () => {
    switch (selectedScenario) {
      case 'keyword_stuffing':
        return {
          baseline: { decision: 'no_signals_detected', score: 0.1, findings: [] },
          modified: { 
            decision: 'review_recommended', 
            score: 0.95, 
            findings: [{ id: 'f1', detector: 'a', category: 'keyword_stuffing', severity: 'high', explanation: 'Suspicious keyword density.' }] 
          }
        };
      case 'prompt_injection':
        return {
          baseline: { decision: 'no_signals_detected', score: 0.1, findings: [] },
          modified: { 
            decision: 'review_recommended', 
            score: 0.99, 
            findings: [{ id: 'f2', detector: 'c', category: 'prompt_injection', severity: 'high', explanation: 'Prompt injection instruction detected.' }] 
          }
        };
      case 'structural_hidden':
        return {
          baseline: { decision: 'no_signals_detected', score: 0.1, findings: [] },
          modified: { 
            decision: 'review_recommended', 
            score: 0.92, 
            findings: [{ id: 'f3', detector: 'b', category: 'invisible_render_mode', severity: 'high', explanation: 'Invisible text render mode.' }] 
          }
        };
      default:
        return {
          baseline: { decision: 'no_signals_detected', score: 0.1, findings: [] },
          modified: { decision: 'no_signals_detected', score: 0.1, findings: [] }
        };
    }
  };

  const results = getResults();

  return (
    <div className="container py-12 max-w-5xl">
      <h1 className="h2 mb-4">Lab: Illustrative Experiments</h1>
      <p className="body text-[--muted] mb-8">Compare baseline inputs against adversarial modifications using pre-calculated analysis artifacts.</p>
      
      <div className="flex gap-4 mb-8 overflow-x-auto pb-2">
        {SCENARIOS.map(s => (
          <button
            key={s.id}
            className={whitespace-nowrap px-4 py-2 rounded-full font-medium text-sm transition-colors }
            onClick={() => setSelectedScenario(s.id)}
          >
            {s.name}
          </button>
        ))}
      </div>

      <div className="grid md:grid-cols-2 gap-8">
        <Card>
          <CardHeader>
            <CardTitle>Baseline Input</CardTitle>
          </CardHeader>
          <div className="mb-4">
            <Badge variant={results.baseline.decision === 'no_signals_detected' ? 'success' : 'danger'}>
              {results.baseline.decision === 'no_signals_detected' ? 'Clean' : 'Flagged'}
            </Badge>
          </div>
          <h3 className="label font-bold text-[--muted] mb-2">Findings</h3>
          <FindingsList findings={results.baseline.findings} />
        </Card>

        <Card className="border-l-4 border-[--primary]">
          <CardHeader>
            <CardTitle>Modified Input</CardTitle>
          </CardHeader>
          <div className="mb-4">
            <Badge variant={results.modified.decision === 'no_signals_detected' ? 'success' : 'danger'}>
              {results.modified.decision === 'no_signals_detected' ? 'Clean' : 'Flagged'}
            </Badge>
          </div>
          <h3 className="label font-bold text-[--muted] mb-2">Findings</h3>
          <FindingsList findings={results.modified.findings} />
        </Card>
      </div>

      <Card className="mt-8">
        <CardHeader><CardTitle>Comparison Table</CardTitle></CardHeader>
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[--border]">
                <th className="p-3 label font-bold text-[--muted]">Run</th>
                <th className="p-3 label font-bold text-[--muted]">Policy Version</th>
                <th className="p-3 label font-bold text-[--muted]">Score</th>
                <th className="p-3 label font-bold text-[--muted]">Decision</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-[--border]">
                <td className="p-3 body">Baseline</td>
                <td className="p-3 body">1.0</td>
                <td className="p-3 font-mono">{results.baseline.score.toFixed(2)}</td>
                <td className="p-3 body">{results.baseline.decision}</td>
              </tr>
              <tr>
                <td className="p-3 body font-medium">Modified</td>
                <td className="p-3 body">1.0</td>
                <td className="p-3 font-mono text-[--danger]">{results.modified.score.toFixed(2)}</td>
                <td className="p-3 body text-[--danger] font-medium">{results.modified.decision}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
