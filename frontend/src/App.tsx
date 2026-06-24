import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ModelDetail from "./pages/ModelDetail";
import ModelDashboard from "./pages/ModelDashboard"; // ✅ NEW
import ValidationQueue from "./pages/ValidationQueue";
import DriftMonitor from "./pages/DriftMonitor";
import RegulatorySubmission from "./pages/RegulatorySubmission";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* ✅ Home */}
        <Route path="/" element={<Dashboard />} />

        {/* ✅ Dashboard route FIRST (more specific) */}
        <Route
          path="/models/:model_id/dashboard"
          element={<ModelDashboard />}
        />

        {/* ✅ Model detail */}
        <Route
          path="/models/:model_id"
          element={<ModelDetail />}
        />

        {/* ✅ Other pages */}
        <Route path="/validation" element={<ValidationQueue />} />
        <Route path="/drift" element={<DriftMonitor />} />
        <Route path="/regulatory" element={<RegulatorySubmission />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;