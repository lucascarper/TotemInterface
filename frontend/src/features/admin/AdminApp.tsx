import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useNavigate } from "react-router-dom";
import { adminSession } from "@/api/admin";
import { Logo } from "@/components/Logo";
import { LoginPage } from "./LoginPage";
import { ConfigPage } from "./ConfigPage";
import { LogsPage } from "./LogsPage";

export default function AdminApp() {
  const [logado, setLogado] = useState(Boolean(adminSession.get()));
  const navigate = useNavigate();

  useEffect(() => {
    const h = () => {
      adminSession.clear();
      setLogado(false);
    };
    window.addEventListener("admin:unauthorized", h);
    return () => window.removeEventListener("admin:unauthorized", h);
  }, []);

  if (!logado) return <LoginPage onLogin={() => setLogado(true)} />;

  const sair = () => {
    adminSession.clear();
    setLogado(false);
    navigate("/admin");
  };

  const tab = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${isActive ? "bg-brand-blue-50 text-brand-blue" : "text-ink-muted hover:bg-surface-alt"}`;

  return (
    <div className="min-h-[100dvh] bg-surface-alt">
      <header className="sticky top-0 z-10 border-b border-surface-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
          <Logo className="h-9" />
          <span className="hidden text-sm font-semibold text-ink-soft sm:block">Painel do totem</span>
          <nav className="ml-auto flex items-center gap-1">
            <NavLink to="/admin/agendas" className={tab}>Agendas</NavLink>
            <NavLink to="/admin/logs" className={tab}>Auditoria</NavLink>
            <a href="/totem" target="_blank" rel="noreferrer" className={tab({ isActive: false })}>Abrir totem ↗</a>
            <button onClick={sair} className="btn-ghost text-sm">Sair</button>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Routes>
          <Route index element={<Navigate to="agendas" replace />} />
          <Route path="agendas" element={<ConfigPage />} />
          <Route path="logs" element={<LogsPage />} />
        </Routes>
      </main>
    </div>
  );
}
