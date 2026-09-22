import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/api/admin";
import { ApiError } from "@/api/client";
import type { LogItem } from "@/api/types";
import { IconRefresh, IconStar } from "@/components/Icons";
import { dataHora } from "@/lib/format";

const ROTULOS: Record<string, string> = {
  BUSCA_PACIENTE: "Busca de paciente",
  BUSCA_AGENDAMENTO: "Busca de agendamento",
  ATUALIZACAO_STATUS: "Atualização de status",
  CRIACAO_AGENDAMENTO: "Criação de encaixe",
  SINCRONIZACAO: "Sincronização",
  ERRO: "Erro",
};

export function LogsPage() {
  const [logs, setLogs] = useState<LogItem[]>([]);
  const [filtro, setFiltro] = useState<"todos" | "sucesso" | "falha">("todos");
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      setLogs(await adminApi.logs(200));
      setErro(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) window.dispatchEvent(new Event("admin:unauthorized"));
      setErro(e instanceof ApiError ? e.message : "Erro ao carregar.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
    const t = window.setInterval(carregar, 30000);
    return () => window.clearInterval(t);
  }, [carregar]);

  const visiveis = logs.filter((l) => (filtro === "todos" ? true : filtro === "sucesso" ? l.sucesso : !l.sucesso));

  return (
    <div className="animate-rise">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Auditoria de operações</h1>
          <p className="mt-1 text-sm text-ink-muted">Cada busca, atualização, encaixe e erro registrado pelo totem. CPFs aparecem mascarados.</p>
        </div>
        <div className="flex items-center gap-2">
          <select className="field w-auto py-2" value={filtro} onChange={(e) => setFiltro(e.target.value as typeof filtro)}>
            <option value="todos">Todos</option>
            <option value="sucesso">Somente sucesso</option>
            <option value="falha">Somente falhas</option>
          </select>
          <button onClick={carregar} className="btn-ghost ring-1 ring-surface-line" disabled={carregando}>
            <IconRefresh className={`h-5 w-5 ${carregando ? "animate-spin" : ""}`} /> Atualizar
          </button>
        </div>
      </div>

      {erro && <p className="mt-4 rounded-lg bg-brand-red-50 px-4 py-3 text-sm font-medium text-brand-red">{erro}</p>}

      <div className="mt-5 overflow-hidden rounded-xl2 bg-white shadow-card ring-1 ring-surface-line">
        <table className="w-full text-sm">
          <thead className="bg-surface-alt text-left text-xs font-semibold uppercase tracking-wider text-ink-soft">
            <tr>
              <th className="px-4 py-3">Quando</th>
              <th className="px-4 py-3">Operação</th>
              <th className="px-4 py-3">Resultado</th>
              <th className="px-4 py-3">CPF</th>
              <th className="px-4 py-3">Tipo</th>
              <th className="px-4 py-3">Agenda / Agendamento</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-line">
            {visiveis.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-ink-muted">{carregando ? "Carregando…" : "Nenhum registro."}</td></tr>
            )}
            {visiveis.map((l) => {
              const preferencial = l.tipo_atendimento === "PREFERENCIAL";
              return (
                <tr key={l.id} className={preferencial ? "bg-brand-red-50/40" : undefined}>
                  <td
                    className={`whitespace-nowrap px-4 py-2.5 font-mono text-xs text-ink-muted ${preferencial ? "border-l-4 border-brand-red" : ""}`}
                  >
                    {dataHora(l.criado_em)}
                  </td>
                  <td className="px-4 py-2.5 font-semibold">{ROTULOS[l.tipo] ?? l.tipo}</td>
                  <td className="px-4 py-2.5">
                    <span className={`badge ${l.sucesso ? "bg-ok-soft text-ok" : "bg-brand-red-50 text-brand-red"}`}>{l.sucesso ? "OK" : "Falha"}</span>
                    <span className="ml-2 text-ink-muted">{l.mensagem}</span>
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs">{l.cpf_mascarado ?? "—"}</td>
                  <td className="px-4 py-2.5">
                    {!l.tipo_atendimento ? (
                      "—"
                    ) : preferencial ? (
                      <span className="badge gap-1 bg-brand-red text-white">
                        <IconStar className="h-3 w-3" /> Preferencial
                      </span>
                    ) : (
                      "Normal"
                    )}
                  </td>
                  <td className="px-4 py-2.5 font-mono text-xs text-ink-muted">
                    {l.agenda_id_sgg ?? "—"} {l.agendamento_id_sgg ? `· ${l.agendamento_id_sgg}` : ""}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
