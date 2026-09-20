import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { FindingsList } from '../components/FindingsList';
import { SourceViewer } from '../components/SourceViewer';
import { FIXTURES } from '../fixtures/analysis-states';

type InputMode = 'pdf' | 'text';
type RequestState = 'idle' | 'analyzing' | 'complete' | 'error';

export default function AnalyzePage() {
  const [mode, setMode] = useState<InputMode>('pdf');
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [error, setError] = useState<string | null>(null);
  
  const [reqState, setReqState] = useState<RequestState>('idle');
  const [result, setResult] = useState<any>(null);
  const reqIdRef = useRef(0);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (!selected) return;
    if (selected.type !== 'application/pdf') {
      setError('Only PDF files are supported.');
      return;
    }
    if (selected.size > 5 * 1024 * 1024) {
      setError('File exceeds 5MB limit.');
      return;
    }
    setError(null);
    setFile(selected);
  };

  const handleAnalyze = () => {
    if (mode === 'pdf' && !file) {
      setError('Please select a PDF file.');
      return;
    }
    if (mode === 'text' && !text.trim()) {
      setError('Input text cannot be empty.');
      return;
    }

    setReqState('analyzing');
    setError(null);
    reqIdRef.current += 1;
    const currentReq = reqIdRef.current;

    // Simulate analysis delay
    setTimeout(() => {
      if (reqIdRef.current !== currentReq) return; // stale request
      setResult(FIXTURES.success);
      setReqState('complete');
    }, 2000);
  };

  const handleCancel = () => {
    reqIdRef.current += 1; // invalidate pending
    setReqState('idle');
  };

  const handleClear = () => {
    if (window.confirm('Clear current session?')) {
      setFile(null);
      setText('');
      setResult(null);
      setReqState('idle');
      setError(null);
    }
  };

  return (
    <div className="container py-12 max-w-4xl">
      <h1 className="h2 mb-8">Analyze Document</h1>

      {reqState === 'idle' && (
        <Card className="mb-8">
          <div className="flex gap-4 border-b border-[--border] mb-6">
            <button
              className={pb-2 px-2 label font-bold }
              onClick={() => setMode('pdf')}
            >
              PDF Upload
            </button>
            <button
              className={pb-2 px-2 label font-bold }
              onClick={() => setMode('text')}
            >
              Raw Text
            </button>
          </div>

          {mode === 'pdf' ? (
            <div className="flex flex-col gap-4">
              <div className="border-2 border-dashed border-[--border] rounded-[10px] h-[220px] flex flex-col items-center justify-center p-6 bg-[--surface-soft]">
                <p className="body mb-4">Drag and drop a PDF here, or click to select.</p>
                <input type="file" accept="application/pdf" className="hidden" id="pdf-upload" onChange={handleFileChange} />
                <label htmlFor="pdf-upload">
                  <span className="inline-flex items-center justify-center font-body font-medium rounded-[10px] min-h-[48px] px-[18px] bg-[--primary] text-white hover:bg-[--primary-hover] cursor-pointer">
                    Choose PDF
                  </span>
                </label>
                <p className="metadata text-[--muted] mt-4">Limit: 5MB.</p>
              </div>
              {file && (
                <div className="flex justify-between items-center p-4 border border-[--border] rounded-[10px]">
                  <span className="body">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
                  <Button variant="tertiary" onClick={() => setFile(null)}>Remove</Button>
                </div>
              )}
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <label className="label font-medium">Resume Text</label>
              <textarea
                className="w-full h-[280px] p-4 border border-[--border] rounded-[10px] bg-[--surface] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[--focus]"
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste document text here..."
              />
              <div className="flex justify-between">
                <span className="metadata text-[--muted]">{text.length} characters</span>
                {text.length > 0 && <Button variant="tertiary" onClick={() => setText('')}>Clear</Button>}
              </div>
            </div>
          )}

          {error && <p className="text-[--danger] mt-4 font-medium">{error}</p>}

          <div className="mt-8 flex gap-4">
            <Button variant="primary" onClick={handleAnalyze}>Analyze Document</Button>
          </div>
        </Card>
      )}

      {reqState === 'analyzing' && (
        <Card className="mb-8 flex flex-col items-center py-12">
          <div className="animate-spin border-4 border-[--border] border-t-[--primary] rounded-full w-12 h-12 mb-6"></div>
          <h2 className="h3 mb-2">Analyzing document...</h2>
          <p className="body text-[--muted] mb-8">Extracting structural and semantic signals.</p>
          <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
        </Card>
      )}

      {reqState === 'complete' && result && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
          <Card className="mb-8 border-l-4 border-[--success]">
            <CardHeader>
              <CardTitle className="text-[--success]">No manipulation signals detected</CardTitle>
            </CardHeader>
            <p className="body text-[--muted] mb-6">In {mode === 'pdf' ? file?.name : 'Raw Text'}. {result.coverage.pages_total} pages analyzed.</p>
            
            <div className="grid md:grid-cols-3 gap-4 mb-6">
               <div className="p-4 bg-[--surface-soft] rounded-[8px]">
                 <strong className="label block mb-1">Text Consistency</strong>
                 <Badge variant="success">OK</Badge>
               </div>
               <div className="p-4 bg-[--surface-soft] rounded-[8px]">
                 <strong className="label block mb-1">Document Structure</strong>
                 <Badge variant={mode === 'text' ? 'neutral' : 'success'}>
                   {mode === 'text' ? 'N/A' : 'OK'}
                 </Badge>
               </div>
               <div className="p-4 bg-[--surface-soft] rounded-[8px]">
                 <strong className="label block mb-1">Semantic Coherence</strong>
                 <Badge variant="success">OK</Badge>
               </div>
            </div>

            <div className="flex gap-4 mb-8">
              <Button variant="secondary" onClick={handleClear}>New Analysis</Button>
            </div>
            
            <div className="grid lg:grid-cols-[40%_1fr] gap-6">
              <div className="flex flex-col gap-4">
                <h3 className="h3">Findings</h3>
                <FindingsList findings={result.findings} />
              </div>
              <div className="flex flex-col gap-4">
                <h3 className="h3">Source Document</h3>
                <SourceViewer mode={mode} />
              </div>
            </div>
          </Card>
        </motion.div>
      )}
    </div>
  );
}
