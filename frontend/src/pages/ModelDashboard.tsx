import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend
} from "recharts";

const ModelDashboard = () => {
  const { model_id } = useParams();
  const [dashboard, setDashboard] = useState<any | undefined>(undefined);

  const fetchDashboard = async () => {
    try {
      const res = await fetch(
        `http://127.0.0.1:8000/api/models/${model_id}`
      );
      const data = await res.json();

      setDashboard(data.dashboard ?? null);
    } catch (err) {
      console.error("Error fetching dashboard:", err);
      setDashboard(null);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [model_id]);

  // ✅ SAFE transform function
  const transformData = (dataObj: any) => {
    if (!dataObj || Object.keys(dataObj).length === 0) return [];

    const keys = Object.keys(dataObj);
    const length = dataObj[keys[0]]?.length || 0;

    return Array.from({ length }, (_, i) => {
      const row: any = { index: i };
      keys.forEach(k => {
        row[k] = dataObj[k]?.[i] ?? null;
      });
      return row;
    });
  };

  if (dashboard === undefined) {
    return <div style={{ padding: "20px" }}>Loading dashboard...</div>;
  }

  if (dashboard === null) {
    return (
      <div style={{ padding: "20px" }}>
        <h3>No Dashboard Available</h3>
        <p>Run monitoring to generate dashboard.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "20px" }}>
      <h2>Model Dashboard</h2>

      <h3 style={{ marginTop: "20px" }}>Visualizations</h3>

      {dashboard.charts?.map((chart: any, index: number) => {
        const config = dashboard.chart_configs?.[index];

        // ✅ guard: missing config
        if (!config || !config.data) {
          return (
            <div
              key={index}
              style={{
                border: "1px solid #ddd",
                padding: "15px",
                marginBottom: "15px",
                borderRadius: "6px",
                background: "#f9f9f9"
              }}
            >
              <h4>{chart.title}</h4>
              <p>No chart data available</p>
            </div>
          );
        }

        const chartData = transformData(config.data);

        const metrics = Object.keys(config.data); // ✅ important fix

        // ✅ guard: empty dataset
        if (chartData.length === 0) {
          return (
            <div
              key={index}
              style={{
                border: "1px solid #ddd",
                padding: "15px",
                marginBottom: "15px",
                borderRadius: "6px",
                background: "#f9f9f9"
              }}
            >
              <h4>{chart.title}</h4>
              <p>No valid data points</p>
            </div>
          );
        }

        return (
          <div
            key={index}
            style={{
              border: "1px solid #ddd",
              padding: "15px",
              marginBottom: "15px",
              borderRadius: "6px",
              background: "#f9f9f9"
            }}
          >
            <h4>{chart.title}</h4>

            <p><b>Type:</b> {chart.type}</p>
            <p><b>Metrics:</b> {metrics.join(", ")}</p>

            {/* ✅ ✅ LINE CHART */}
            {chart.type === "line" && (
              <LineChart width={500} height={250} data={chartData}>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="index" />
                <YAxis />
                <Tooltip />
                <Legend />

                {metrics.map((m: string) => (
                  <Line
                    key={m}
                    type="monotone"
                    dataKey={m}
                    stroke={
                      m === "psi"
                        ? "#ff4d4f"
                        : m === "accuracy"
                        ? "#1890ff"
                        : m === "precision"
                        ? "#82ca9d"
                        : "#8884d8"
                    }
                  />
                ))}
              </LineChart>
            )}

            {/* ✅ ✅ BAR CHART */}
            {chart.type === "bar" && (
              <BarChart width={500} height={250} data={chartData}>
                <CartesianGrid stroke="#ccc" />
                <XAxis dataKey="index" />
                <YAxis />
                <Tooltip />
                <Legend />

                {metrics.map((m: string) => (
                  <Bar key={m} dataKey={m} fill="#8884d8" />
                ))}
              </BarChart>
            )}
          </div>
        );
      })}

      {/* ✅ Insights */}
      <h3 style={{ marginTop: "30px" }}>Insights</h3>

      {dashboard.insights?.length > 0 ? (
        <ul>
          {dashboard.insights.map((ins: string, i: number) => (
            <li key={i}>{ins}</li>
          ))}
        </ul>
      ) : (
        <p>No insights available</p>
      )}
    </div>
  );
};

export default ModelDashboard;