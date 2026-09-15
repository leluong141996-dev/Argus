import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type ConfigInfo } from "../api";

export function NewRun() {
  const [configs, setConfigs] = useState<ConfigInfo[]>([]);
  const [selected, setSelected] = useState("");
  const [provider, setProvider] = useState("");
  const [runGate, setRunGate] = useState(true);
  const [error, setError] = useState("");
  const nav = useNavigate();

  useEffect(() => {
    api.listConfigs().then((c) => { setConfigs(c); if (c[0]) setSelected(c[0].name); })
      .catch((e) => setError(String(e)));
  }, []);

  async function run() {
    setError("");
    try {
      const { run_id } = await api.startRun({
        config: selected, run_gate: runGate,
        provider_override: provider || undefined,
      });
      nav(`/runs/${run_id}`);
    } catch (e) { setError(String(e)); }
  }

  return (
    <div className="card">
      <h2>New Run</h2>
      {error && <p className="error">{error}</p>}
      <label className="field">
        <span className="label">Config</span>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {configs.map((c) => <option key={c.name} value={c.name}>{c.name} ({c.task})</option>)}
        </select>
      </label>
      <label className="field">
        <span className="label">Provider override</span>
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="">(from config)</option>
          <option value="mock">mock</option>
          <option value="groq">groq</option>
        </select>
      </label>
      <label className="field check">
        <input type="checkbox" checked={runGate}
          onChange={(e) => setRunGate(e.target.checked)} />
        run gate first
      </label>
      <button className="btn btn-primary" onClick={run} disabled={!selected}>Run</button>
    </div>
  );
}
