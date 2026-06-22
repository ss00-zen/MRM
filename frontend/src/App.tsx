import { BrowserRouter, Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ModelDetail from "./pages/ModelDetail";
import ValidationQueue from "./pages/ValidationQueue"
import DriftMonitor from "./pages/DriftMonitor";
import RegulatorySubmission from "./pages/RegulatorySubmission";


function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/model/:model_id" element={<ModelDetail />} />
        <Route path="/validation" element={<ValidationQueue />} />
        <Route path="/drift" element={<DriftMonitor />} />
        <Route path="/regulatory" element={<RegulatorySubmission />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
``