import { useEffect, useState } from "react";

const RegulatorySubmission = () => {
  const [models, setModels] = useState<any[]>([]);

  const fetchModels = async () => {
    const res = await fetch("http://127.0.0.1:8000/api/models/");
    const data = await res.json();
    setModels(Array.isArray(data) ? data : []);
  };

  useEffect(() => {
    fetchModels();
  }, []);

  if (models.length === 0) {
    return <div>No models available</div>;
  }

  return (
    <div style={{ padding: "20px" }}>
      <h2>Regulatory Submission</h2>

      <table border={1} cellPadding={10} style={{ width: "100%" }}>
        <thead>
          <tr>
            <th>Model Name</th>
            <th>Validation Status</th>
            <th>Compliance (SR 11-7)</th>
          </tr>
        </thead>

        <tbody>
          {models.map((m: any) => (
            <tr key={m.model_id}>
              <td>{m.model_name}</td>

              <td>{m.validation_status}</td>

              <td style={{ color: m.sr117_compliant ? "green" : "red" }}>
                {m.sr117_compliant ? "Compliant ✅" : "Non-Compliant ❌"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default RegulatorySubmission;
