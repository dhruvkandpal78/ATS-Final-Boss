import { Routes, Route, Link } from 'react-router-dom';
import Gallery from './Gallery';
import Landing from './pages/Landing';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[--canvas]">
      <header className="px-[--space-24] py-[--space-16] border-b border-[--border] flex flex-col md:flex-row md:items-center justify-between gap-4 sticky top-0 bg-[--canvas]/90 backdrop-blur z-50">
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
      </header>
      <main className="pb-[--space-64]">{children}</main>
    </div>
  );
}

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
