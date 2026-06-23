import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import ModelsTable from "./ModelsTable";

const Dashboard = () => {
  const [models, setModels] = useState<any[]>([]);
  const navigate = useNavigate();

  const fetchModels = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/api/models/");
      const data = await res.json();
      setModels(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Error fetching models:", err);
      setModels([]);
    }
  };

  useEffect(() => {
    // ✅ Initial load ONLY (no polling)
    fetchModels();
  }, []);

  return (
    <div style={{ padding: "20px" }}>
      <h2>Model Dashboard</h2>

      <div style={{ marginBottom: "15px", display: "flex", gap: "10px" }}>
        <button onClick={() => navigate("/validation")}>
          Validation Queue
        </button>

        <button onClick={() => navigate("/drift")}>
          Drift Monitor
        </button>

        <button onClick={() => navigate("/regulatory")}>
          Regulatory
        </button>
      </div>

      <ModelsTable models={models} refresh={fetchModels} />
    </div>
  );
};

export default Dashboard;
