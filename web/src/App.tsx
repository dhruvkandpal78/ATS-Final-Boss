import { Routes, Route, Link } from 'react-router-dom';
import Gallery from './Gallery';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <header className="px-[--space-24] py-[--space-16] border-b border-[--border] flex items-center justify-between">
        <strong className="h3 text-[--ink]">ATS Final Boss</strong>
        <nav className="flex gap-[--space-24]">
          <Link to="/" className="label text-[--muted] hover:text-[--ink]">How it works</Link>
          <Link to="/methodology" className="label text-[--muted] hover:text-[--ink]">Methodology</Link>
          <Link to="/lab" className="label text-[--muted] hover:text-[--ink]">Lab</Link>
          <Link to="/analyze" className="label text-[--muted] hover:text-[--ink]">Analyze a resume</Link>
          <Link to="/gallery" className="label text-[--primary] font-bold">Design System</Link>
        </nav>
      </header>
      <main className="min-h-screen pb-[--space-64]">{children}</main>
    </div>
  );
}

function Landing() { return <div className="container py-[--space-32]"><h1 className="h1">Landing Page (U03)</h1></div>; }
function Analyze() { return <div className="container py-[--space-32]"><h1 className="h1">Analyze (U05/U06)</h1></div>; }
function Lab() { return <div className="container py-[--space-32]"><h1 className="h1">Lab (U08)</h1></div>; }
function Methodology() { return <div className="container py-[--space-32]"><h1 className="h1">Methodology</h1></div>; }

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/lab" element={<Lab />} />
        <Route path="/methodology" element={<Methodology />} />
        <Route path="/gallery" element={<Gallery />} />
      </Routes>
    </Layout>
  );
}
