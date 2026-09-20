import React from 'react';

export function SourceViewer({ mode }: { mode: 'pdf' | 'text' }) {
  return (
    <div className="w-full h-[600px] border border-[--border] rounded-[10px] bg-[#e0e3dd] flex items-center justify-center relative overflow-hidden">
      {/* Placeholder geometry for PDF/Text rendering */}
      <div className="absolute inset-4 bg-white shadow-sm flex flex-col p-8">
        <p className="label font-bold text-[--muted] mb-8">{mode === 'pdf' ? 'PDFSourceViewer Placeholder' : 'TextSourceViewer Placeholder'}</p>
        
        {/* Placeholder lines */}
        <div className="w-3/4 h-4 bg-gray-200 rounded mb-4"></div>
        <div className="w-full h-2 bg-gray-100 rounded mb-2"></div>
        <div className="w-5/6 h-2 bg-gray-100 rounded mb-2"></div>
        <div className="w-full h-2 bg-gray-100 rounded mb-8"></div>
        
        {/* Placeholder highlight */}
        <div className="w-1/2 h-8 bg-[--warning] opacity-20 rounded border border-[--warning]"></div>
      </div>
    </div>
  );
}
