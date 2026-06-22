import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import Workflow from "./Workflow";

const ModelDetail = () => {
  const { model_id } = useParams();
  const wsRef = useRef<WebSocket | null>(null);

  const [model, setModel] = useState<any>(null);

  const fetchModel = async () => {
    const res = await fetch(`http://127.0.0.1:8000/api/models/${model_id}`);
    setModel(await res.json());
  };

  const runMonitor = async () => {
    await fetch(`http://127.0.0.1:8000/api/models/${model_id}/monitor`, {
      method: "POST",
    });
  };

  useEffect(() => {
    fetchModel();

    if (!wsRef.current) {
      const ws = new WebSocket("ws://127.0.0.1:8000/ws/models");

      ws.onmessage = async (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === "model_update" && msg.model_id === model_id) {
          console.log("🔄 Updating detail...");
          await fetchModel();
        }
      };

      wsRef.current = ws;
    }

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, []);

  if (!model) return <div>Loading...</div>;

  return (
    <div>
      <h2>{model.model_name}</h2>

      <button onClick={runMonitor}>Monitor</button>

      <p>Status: {model.validation_status}</p>
      <p>PSI: {model.perf_psi}</p>

      <Workflow status={model.validation_status} />
    </div>
  );
};

export default ModelDetail;