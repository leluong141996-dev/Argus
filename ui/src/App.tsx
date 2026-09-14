import { Link, Route, Routes } from "react-router-dom";

function Placeholder({ title }: { title: string }) {
  return <h2>{title}</h2>;
}

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui", padding: 16 }}>
      <nav style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Link to="/">New Run</Link>
        <Link to="/runs">History</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Placeholder title="New Run" />} />
        <Route path="/runs" element={<Placeholder title="History" />} />
        <Route path="/runs/:id" element={<Placeholder title="Follow" />} />
      </Routes>
    </div>
  );
}
