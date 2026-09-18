import { FormEvent, useState } from "react";
import { adminApi, adminSession } from "@/api/admin";
import { ApiError } from "@/api/client";
import { Logo } from "@/components/Logo";

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setErro(null);
    setCarregando(true);
    try {
      const { access_token } = await adminApi.login(username, password);
      adminSession.set(access_token);
      onLogin();
    } catch (err) {
      setErro(err instanceof ApiError ? err.message : "Falha ao entrar.");
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="brand-arc grid min-h-[100dvh] place-items-center px-4">
      <form onSubmit={submit} className="w-full max-w-sm animate-rise rounded-xl3 bg-white p-8 shadow-card ring-1 ring-surface-line">
        <Logo className="mx-auto h-12" />
        <h1 className="mt-6 text-center text-xl font-bold">Painel administrativo</h1>
        <p className="mt-1 text-center text-sm text-ink-muted">Configuração do totem de recepção</p>

        <label className="mt-6 block text-sm font-semibold">
          Usuário
          <input className="field mt-1" value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required autoFocus />
        </label>
        <label className="mt-4 block text-sm font-semibold">
          Senha
          <input className="field mt-1" type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
        </label>
        {erro && <p className="mt-3 rounded-lg bg-brand-red-50 px-3 py-2 text-sm font-medium text-brand-red">{erro}</p>}
        <button className="btn-primary mt-6 w-full py-3" disabled={carregando}>
          {carregando ? "Entrando…" : "Entrar"}
        </button>
      </form>
    </div>
  );
}
