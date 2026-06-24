import { useEffect, useRef, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

const ModelDetail = () => {
  const { model_id } = useParams();
  const navigate = useNavigate(); // ✅ NEW
  const wsRef = useRef<WebSocket | null>(null);

  const [model, setModel] = useState<any>(null);

  const fetchModel = async () => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/models/${model_id}`
      );
      const data = await res.json();
      setModel(data);
    } catch (err) {
      console.error("Error fetching model:", err);
    }
  };

  const runMonitor = async () => {
    await fetch(
      `http://127.0.0.1:8000/api/models/${model_id}/monitor`,
      { method: "POST" }
    );
  };

  const goToDashboard = () => {
    navigate(`/models/${model_id}/dashboard`);
  };

  useEffect(() => {
    fetchModel();

    if (wsRef.current) return;

    const ws = new WebSocket("ws://127.0.0.1:8000/ws/models");

    ws.onopen = () => {
      console.log("✅ WS connected (detail)");
    };

    ws.onmessage = async (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "model_update" && msg.model_id === model_id) {
        console.log("🔄 Updating model detail...");
        await fetchModel();
      }
    };

    ws.onerror = (err) => {
      console.error("❌ WS error:", err);
    };

    ws.onclose = () => {
      wsRef.current = null;
    };

    wsRef.current = ws;

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [model_id]);

  if (!model) return <div>Loading...</div>;

  return (
    <div style={{ padding: "20px" }}>
      <h2>{model.model_name}</h2>

      <button onClick={runMonitor}>Monitor</button>

      {/* ✅ NEW DASHBOARD BUTTON */}
      <button
        onClick={goToDashboard}
        style={{ marginLeft: "10px" }}
      >
        View Dashboard
      </button>

      <p><b>Model Type:</b> {model.model_type}</p>
      <p><b>PSI:</b> {model.perf_psi}</p>

      <p>
        <b>SR 11-7 Compliance:</b>{" "}
        {model.sr117_compliant ? "✅" : "❌"}
      </p>

      {/* ✅ Monitoring */}
      <h3 style={{ marginTop: "20px" }}>Monitoring Explanation</h3>
      {model.monitoring_explanation ? (
        <pre style={{
          background: "#f5f5f5",
          padding: "10px",
          borderRadius: "6px",
          whiteSpace: "pre-wrap"
        }}>
          {JSON.stringify(model.monitoring_explanation, null, 2)}
        </pre>
      ) : (
        <p>No monitoring explanation available</p>
      )}

      {/* ✅ History Analysis */}
      <h3 style={{ marginTop: "20px" }}>History Analysis</h3>
      {model.history_analysis ? (
        <pre style={{
          background: "#eef7ff",
          padding: "10px",
          borderRadius: "6px",
          whiteSpace: "pre-wrap"
        }}>
          {JSON.stringify(model.history_analysis, null, 2)}
        </pre>
      ) : (
        <p>No history analysis available</p>
      )}

      {/* ✅ Regulatory */}
      <h3 style={{ marginTop: "20px" }}>Regulatory Explanation</h3>
      {model.regulatory_explanation ? (
        <pre style={{
          background: "#f5f5f5",
          padding: "10px",
          borderRadius: "6px",
          whiteSpace: "pre-wrap"
        }}>
          {JSON.stringify(model.regulatory_explanation, null, 2)}
        </pre>
      ) : (
        <p>No regulatory explanation available</p>
      )}

      {/* ✅ Jira Tickets */}
      <h3 style={{ marginTop: "20px" }}>Jira Tickets</h3>

      {!model.incidents || model.incidents.length === 0 ? (
        <p>No Jira tickets</p>
      ) : (
        <table border={1} cellPadding={10} style={{ width: "100%" }}>
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Type</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {model.incidents.map((ticket: any) => (
              <tr key={ticket.key}>
                <td>{ticket.key}</td>
                <td>{ticket.validation_type}</td>
                <td
                  style={{
                    color: ticket.status === "approval" ? "green" : "red",
                    fontWeight: "bold",
                  }}
                >
                  {ticket.status}
                </td>
                <td>{ticket.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

export default ModelDetail;