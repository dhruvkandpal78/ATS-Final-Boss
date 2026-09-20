import React from 'react';
import { Badge } from './ui/Badge';
import { Button } from './ui/Button';

export function FindingsList({ findings }: { findings: any[] }) {
  if (!findings || findings.length === 0) {
    return (
      <div className="py-12 flex flex-col items-center justify-center text-center text-[--muted]">
        <p className="body mb-2">No findings to display.</p>
        <p className="metadata">Clear filters or run a new analysis.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {findings.map((f, i) => (
        <div key={i} className="p-4 border border-[--border] rounded-[10px] bg-[--surface] hover:border-[--primary-soft] cursor-pointer transition-colors">
          <div className="flex gap-2 mb-2">
            <Badge variant={f.severity === 'high' ? 'danger' : 'warning'}>{f.severity}</Badge>
            <Badge variant="neutral">{f.category}</Badge>
          </div>
          <p className="body text-[--ink]">{f.explanation}</p>
        </div>
      ))}
    </div>
  );
}
