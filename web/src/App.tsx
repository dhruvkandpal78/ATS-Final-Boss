import React, { useState, useEffect } from 'react';
import { Routes, Route, Link } from 'react-router-dom';
import { motion, useScroll, useReducedMotion } from 'framer-motion';
import Gallery from './Gallery';
import Landing from './pages/Landing';
import AnalyzePage from './pages/AnalyzePage';
import LabPage from './pages/LabPage';

function Layout({ children }: { children: React.ReactNode }) {
  const { scrollY } = useScroll();
  const [scrolled, setScrolled] = useState(false);
  const prefersReduced = useReducedMotion();

  useEffect(() => {
    return scrollY.on("change", (latest) => {
      setScrolled(latest > 24);
    });
  }, [scrollY]);

  return (
    <div className="min-h-screen bg-[--canvas]">
      <motion.header 
        initial={false}
        animate={{ 
          backgroundColor: scrolled ? 'rgba(255, 255, 255, 0.9)' : 'rgba(246, 245, 241, 0)',
          borderColor: scrolled ? 'var(--border)' : 'transparent'
        }}
        transition={{ duration: prefersReduced ? 0 : 0.18, ease: "easeInOut" }}
        className="px-[--space-24] py-[--space-16] border-b flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 backdrop-blur z-50"
      >
        <strong className="h3 text-[--ink] flex items-center gap-2">
          <div className="w-6 h-6 bg-[--primary] rounded-sm"></div>
          ATS Final Boss
        </strong>
        <nav className="flex flex-wrap gap-[--space-24]">
          <Link to="/" className="label text-[--muted] hover:text-[--ink]">How it works</Link>
          <Link to="/methodology" className="label text-[--muted] hover:text-[--ink]">Methodology</Link>
          <Link to="/lab" className="label text-[--muted] hover:text-[--ink]">Lab</Link>
          <Link to="/analyze" className="label text-[--primary] font-medium hover:text-[--primary-hover]">Analyze a resume</Link>
        </nav>
      </motion.header>
      <main className="pb-[--space-64]">{children}</main>
    </div>
  );
}

function Methodology() { return <div className="container py-[--space-32]"><h1 className="h1">Methodology</h1></div>; }

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/analyze" element={<AnalyzePage />} />
        <Route path="/lab" element={<LabPage />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/gallery" element={<Gallery />} />
      </Routes>
    </Layout>
  );
}
