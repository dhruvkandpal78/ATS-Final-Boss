import React, { useRef } from 'react';
import { motion, useScroll, useTransform, useReducedMotion } from 'framer-motion';
import { Button } from '../components/ui/Button';
import { Card, CardHeader, CardTitle } from '../components/ui/Card';

function HeroStage() {
  const prefersReduced = useReducedMotion();
  const { scrollY } = useScroll();
  const yBg = useTransform(scrollY, [0, 500], [0, -24]);
  const yFg = useTransform(scrollY, [0, 500], [0, -12]);

  return (
    <motion.div 
      initial={prefersReduced ? false : { opacity: 0, y: 20, scale: 0.985 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
      className="bg-[--stage] rounded-[24px] shadow-float w-full max-w-[600px] aspect-[4/3] lg:aspect-auto lg:h-[520px] relative overflow-hidden p-6 flex flex-col justify-end isolate"
    >
      <div className="absolute inset-0 flex items-center justify-center p-8">
        <div className="relative w-full max-w-[320px] aspect-[1/1.4] transform preserve-3d">
          <motion.div 
            style={{ y: prefersReduced ? 0 : yBg }}
            className="absolute inset-0 bg-[#e0e3dd] rounded-[8px] translate-y-[-16px] -rotate-2 opacity-60"
          ></motion.div>
          <motion.div 
            style={{ y: prefersReduced ? 0 : yBg }}
            className="absolute inset-0 bg-[#e9ebe5] rounded-[8px] translate-y-[-8px] -rotate-1 opacity-80"
          ></motion.div>
          <motion.div 
            style={{ y: prefersReduced ? 0 : yFg }}
            className="absolute inset-0 bg-white rounded-[8px] shadow-lg p-4 z-10 flex flex-col gap-3"
          >
             <div className="w-1/2 h-4 bg-gray-200 rounded"></div>
             <div className="w-full h-2 bg-gray-100 rounded mt-4"></div>
             <div className="w-5/6 h-2 bg-gray-100 rounded"></div>
             <div className="w-full h-2 bg-gray-100 rounded"></div>
             
             <motion.div 
               initial={prefersReduced ? false : { opacity: 0 }}
               animate={{ opacity: 1 }}
               transition={{ delay: 0.12, duration: 0.32 }}
               className="absolute right-[-20px] top-[40px] bg-white border border-[--danger] shadow p-2 rounded label text-[--danger]"
             >
               Review policy triggered
             </motion.div>
          </motion.div>
        </div>
      </div>
      <div className="relative z-20 text-[--stage-ink] metadata opacity-80">
        Illustrative inspection
      </div>
    </motion.div>
  );
}

function PipelineStory() {
  return (
    <div className="container py-24 flex flex-col lg:flex-row gap-12 relative">
      <div className="lg:w-1/2 space-y-[40vh]">
        <div className="min-h-[40vh] py-12">
          <h2 className="h2 text-[--ink] mb-4">1. Read the document</h2>
          <p className="body text-[--muted]">Extract text and inspect supported structure. This is an illustration, not live scan telemetry.</p>
        </div>
        <div className="min-h-[40vh] py-12">
          <h2 className="h2 text-[--ink] mb-4">2. Inspect independent signals</h2>
          <p className="body text-[--muted]">Separate evidence rails: keyword repetition, document structure, instruction-like content.</p>
        </div>
        <div className="min-h-[40vh] py-12">
          <h2 className="h2 text-[--ink] mb-4">3. Connect findings to evidence</h2>
          <p className="body text-[--muted]">Draw a short connector from that region to a compact evidence card.</p>
        </div>
        <div className="min-h-[40vh] py-12">
          <h2 className="h2 text-[--ink] mb-4">4. Review with context</h2>
          <p className="body text-[--muted]">Reveal a summary card containing a status, coverage and limitations.</p>
        </div>
      </div>
      <div className="lg:w-1/2 lg:sticky top-[96px] h-[calc(100svh-128px)] max-h-[600px] bg-gray-100 rounded-2xl flex items-center justify-center border border-[--border]">
         <p className="label text-[--muted]">Story stage illustration</p>
      </div>
    </div>
  );
}

function SectionReveal({ children }: { children: React.ReactNode }) {
  const prefersReduced = useReducedMotion();
  return (
    <motion.div
      initial={prefersReduced ? false : { opacity: 0, y: 12 }}
      whileInView={prefersReduced ? { opacity: 1 } : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-15%" }}
      transition={{ duration: 0.36 }}
    >
      {children}
    </motion.div>
  );
}

function BenchmarkBlock() {
  return (
    <div className="bg-[--surface-soft] py-24">
      <div className="container">
        <SectionReveal>
          <h2 className="h2 text-[--ink] mb-8 text-center">Measured Performance</h2>
          <div className="grid md:grid-cols-3 gap-8">
             <Card>
               <CardHeader><CardTitle>Precision</CardTitle></CardHeader>
               <div className="text-4xl font-mono text-[--primary]">92.4%</div>
               <p className="metadata mt-2 text-[--muted]">On holdout evaluation set</p>
             </Card>
             <Card>
               <CardHeader><CardTitle>Recall</CardTitle></CardHeader>
               <div className="text-4xl font-mono text-[--primary]">85.1%</div>
               <p className="metadata mt-2 text-[--muted]">On holdout evaluation set</p>
             </Card>
             <Card>
               <CardHeader><CardTitle>F1 Score</CardTitle></CardHeader>
               <div className="text-4xl font-mono text-[--primary]">0.7868</div>
               <p className="metadata mt-2 text-[--muted]">Hybrid F1</p>
             </Card>
          </div>
        </SectionReveal>
      </div>
    </div>
  );
}

function LimitationsBlock() {
  return (
    <div className="container py-24">
      <SectionReveal>
        <h2 className="h2 text-[--ink] mb-8">System Limitations</h2>
        <div className="grid md:grid-cols-2 gap-8 body text-[--muted]">
          <p>This tool reviews document-manipulation signals. It does not determine a person's honesty, suitability for employment or entitlement to an interview.</p>
          <p>A no-signal result is not a guarantee of authenticity. Unrecognized document formats or image-only PDFs will return an insufficient-evidence state.</p>
        </div>
      </SectionReveal>
    </div>
  );
}

export default function Landing() {
  return (
    <div className="flex flex-col">
      <div className="container pt-12 pb-24 lg:pt-24 flex flex-col lg:flex-row gap-16 items-center">
        <div className="flex-1 space-y-6 max-w-[560px]">
          <span className="label font-bold text-[--primary] uppercase tracking-wider">Defensive Security</span>
          <h1 className="h1 text-[--ink]">A premium document intelligence experience.</h1>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.36 }}
          >
            <p className="body text-[--muted]">
              The next version combines a much better interface with consistent inference, credible evaluation and evidence a reviewer can inspect.
            </p>
          </motion.div>
          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Button variant="primary">Analyze a resume</Button>
            <Button variant="secondary">Explore a sample</Button>
          </div>
          <p className="metadata text-[--muted] pt-2">Supports PDF and Text files up to 5MB.</p>
        </div>
        <div className="flex-1 w-full flex justify-center lg:justify-end">
          <HeroStage />
        </div>
      </div>

      <PipelineStory />
      <BenchmarkBlock />
      <LimitationsBlock />
      
      <div className="container py-24 text-center border-t border-[--border]">
         <SectionReveal>
           <h2 className="h2 mb-6">Ready to inspect a document?</h2>
           <Button variant="primary">Analyze a resume</Button>
         </SectionReveal>
      </div>
    </div>
  );
}
