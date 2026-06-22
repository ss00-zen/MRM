import { useEffect, useState } from "react";

const DriftMonitor = () => {
  const [models, setModels] = useState<any[]>([]);

  const fetchModels = async () => {
    const res = await fetch("http://127.0.0.1:8000/api/models/");
    const data = await res.json();

    // ✅ show only models with drift
    const filtered = (data || []).filter(
      (m: any) => m.perf_psi !== null && m.perf_psi !== undefined
    );

    setModels(filtered);
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const getDriftColor = (psi: number) => {
    if (psi > 0.15) return "red";
    if (psi > 0.08) return "orange";
    return "green";
  };

  if (models.length === 0) {
    return <div>No drift data available</div>;
  }

  return (
    <div style={{ padding: "20px" }}>
      <h2>Drift Monitor</h2>

      <table border={1} cellPadding={10} style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Model</th>
            <th>Drift (PSI)</th>
            <th>Status</th>
          </tr>
        </thead>

        <tbody>
          {models.map((m: any) => (
            <tr key={m.model_id}>
              <td>{m.model_name}</td>

              <td style={{ color: getDriftColor(m.perf_psi) }}>
                {Number(m.perf_psi).toFixed(2)}
              </td>

              <td style={{
                color: m.perf_psi > 0.15 ? "red" : "green"
              }}>
                {m.perf_psi > 0.15
                  ? "Threshold Breached"
                  : "Within Limit"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DriftMonitor;