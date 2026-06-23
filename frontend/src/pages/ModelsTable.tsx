import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";

const ModelsTable = ({ models = [], refresh }: any) => {
  const navigate = useNavigate();
  const wsRef = useRef<WebSocket | null>(null);

  const runMonitor = async (model_id: string) => {
    await fetch(
      `http://127.0.0.1:8000/api/models/${model_id}/monitor`,
      { method: "POST" }
    );

    if (refresh) {
      await refresh(); // ✅ immediate refresh
    }
  };

  useEffect(() => {
    if (!wsRef.current) {
      const ws = new WebSocket("ws://127.0.0.1:8000/ws/models");

      ws.onopen = async () => {
        console.log("✅ WS connected");
        if (refresh) {
          await refresh(); // ✅ reload on connect
        }
      };

      ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "model_update" && refresh) {
          console.log("🔄 Updating table...");
          await refresh();
          setTimeout(() => refresh(), 200);
        }
      };

      ws.onclose = () => console.log("❌ WS closed");

      wsRef.current = ws;
    }

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  return (
    <table border={1} cellPadding={10} style={{ width: "100%" }}>
      <thead>
        <tr>
          <th>Name</th>
          <th>Type</th>
          <th>Status</th>
          <th>Drift</th>
          <th>Compliance</th>
          <th>Actions</th>
        </tr>
      </thead>

      <tbody>
        {models.map((m: any) => (
          <tr key={m.model_id}>
            <td>{m.model_name}</td>
            <td>{m.model_type}</td>

            {/* ✅ Active / No Active Tickets */}
            <td
              style={{
                color: m.has_open_incidents ? "red" : "green",
                fontWeight: "bold",
              }}
            >
              {m.validation_status}
            </td>

            <td>{m.perf_psi ?? "-"}</td>

            <td>{m.sr117_compliant ? "✅" : "❌"}</td>

            <td>
              <button onClick={() => runMonitor(m.model_id)}>
                Monitor
              </button>

              <button onClick={() => navigate(`/model/${m.model_id}`)}>
                View
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default ModelsTable;
