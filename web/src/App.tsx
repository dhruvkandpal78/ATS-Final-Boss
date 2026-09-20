import { Routes, Route, Link } from 'react-router-dom';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <header style={{ padding: '1rem', borderBottom: '1px solid #ccc' }}>
        <strong>ATS Final Boss</strong>
        <nav style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem' }}>
          <Link to="/">How it works</Link>
          <Link to="/methodology">Methodology</Link>
          <Link to="/lab">Lab</Link>
          <Link to="/analyze">Analyze a resume</Link>
        </nav>
      </header>
      <main style={{ padding: '1rem' }}>{children}</main>
    </div>
  );
}

function Landing() { return <div><h1>Landing Page (U03)</h1></div>; }
function Analyze() { return <div><h1>Analyze (U05/U06)</h1></div>; }
function Lab() { return <div><h1>Lab (U08)</h1></div>; }
function Methodology() { return <div><h1>Methodology</h1></div>; }

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/lab" element={<Lab />} />
        <Route path="/methodology" element={<Methodology />} />
      </Routes>
    </Layout>
  );
}
