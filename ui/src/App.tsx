import { Link, Route, Routes } from "react-router-dom";
import { NewRun } from "./pages/NewRun";
import { History } from "./pages/History";
import { Follow } from "./pages/Follow";

export default function App() {
  return (
    <div style={{ fontFamily: "system-ui", padding: 16 }}>
      <nav style={{ display: "flex", gap: 12, marginBottom: 16 }}>
        <Link to="/">New Run</Link>
        <Link to="/runs">History</Link>
      </nav>
      <Routes>
        <Route path="/" element={<NewRun />} />
        <Route path="/runs" element={<History />} />
        <Route path="/runs/:id" element={<Follow />} />
      </Routes>
    </div>
  );
}
