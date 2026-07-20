import { AnimatePresence } from "framer-motion";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import Landing from "./pages/Landing";
import Dashboard from "./pages/Dashboard";
import Marketplace from "./pages/Marketplace";
import AIPredictions from "./pages/AIPredictions";
import Blockchain from "./pages/Blockchain";
import SmartGrid from "./pages/SmartGrid";

export default function App() {
  const location = useLocation();
  return <AnimatePresence mode="wait"><Routes location={location} key={location.pathname}>
    <Route path="/" element={<Landing />} />
    <Route element={<Layout />}><Route path="/dashboard" element={<Dashboard />} /><Route path="/marketplace" element={<Marketplace />} /><Route path="/ai-predictions" element={<AIPredictions />} /><Route path="/blockchain" element={<Blockchain />} /><Route path="/smart-grid" element={<SmartGrid />} /></Route>
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes></AnimatePresence>;
}
