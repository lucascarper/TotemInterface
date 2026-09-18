import { Navigate, Route, Routes } from "react-router-dom";
import TotemApp from "./features/totem/TotemApp";
import AdminApp from "./features/admin/AdminApp";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/totem" replace />} />
      <Route path="/totem" element={<TotemApp />} />
      <Route path="/admin/*" element={<AdminApp />} />
      <Route path="*" element={<Navigate to="/totem" replace />} />
    </Routes>
  );
}
