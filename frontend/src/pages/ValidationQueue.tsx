import { useEffect, useState } from "react";

const ValidationQueue = () => {
  const [models, setModels] = useState<any[]>([]);

  const fetchModels = async () => {
    const res = await fetch("http://127.0.0.1:8000/api/models/");
    const data = await res.json();

    // ✅ only models still in validation
    const filtered = (data || []).filter(
      (m: any) =>
        m.validation_status !== "approval" &&
        m.validation_status !== "approved"
    );

    setModels(filtered);
  };

  useEffect(() => {
    fetchModels();
  }, []);

  if (!models || models.length === 0) {
    return <div>No models in validation queue</div>;
  }

  return (
    <div style={{ padding: "20px" }}>
      <h2>Validation Queue</h2>

      <table border={1} cellPadding={10} style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Model Name</th>
            <th>Validation Stage</th>
            <th>Type</th>
          </tr>
        </thead>

        <tbody>
          {models.map((m: any) => (
            <tr key={m.model_id}>
              <td>{m.model_name}</td>
              <td>{m.validation_status}</td>
              <td>{m.model_type}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ValidationQueue;
