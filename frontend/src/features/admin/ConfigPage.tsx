import { useCallback, useEffect, useState } from "react";
import { adminApi } from "@/api/admin";
import { ApiError } from "@/api/client";
import type { ConfiguracaoAgenda, StatusSincronizacao } from "@/api/types";
import { IconRefresh } from "@/components/Icons";
import { dataHora } from "@/lib/format";
import { TotemCard } from "./TotemCard";

function tratar(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) window.dispatchEvent(new Event("admin:unauthorized"));
  return e instanceof ApiError ? e.message : "Erro inesperado.";
}

export function ConfigPage() {
  const [itens, setItens] = useState<ConfiguracaoAgenda[]>([]);
  const [original, setOriginal] = useState<string>("");
  const [sync, setSync] = useState<StatusSincronizacao | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);
  // A sincronização pode tirar da recepção uma agenda que ficou inativa: recarrega o cartão.
  const [versaoTotem, setVersaoTotem] = useState(0);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const [cfg, st] = await Promise.all([adminApi.configuracoes(), adminApi.statusSincronizacao()]);
      setItens(cfg);
      setOriginal(JSON.stringify(cfg));
      setSync(st);
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const alterado = JSON.stringify(itens) !== original;
  const monitoradas = itens.filter((i) => i.monitorada);

  const atualizar = (id: string, patch: Partial<ConfiguracaoAgenda>) =>
    setItens((prev) => prev.map((i) => (i.agenda_id_sgg === id ? { ...i, ...patch } : i)));

  const salvar = async () => {
    setOcupado(true);
    setMsg(null);
    try {
      await adminApi.salvar(
        itens.map(({ agenda_id_sgg, monitorada }) => ({ agenda_id_sgg, monitorada })),
      );
      setOriginal(JSON.stringify(itens));
      setMsg({ tipo: "ok", texto: "Configuração salva. O totem já usa as novas regras." });
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setOcupado(false);
    }
  };

  const sincronizar = async () => {
    setOcupado(true);
    setMsg(null);
    try {
      const r = await adminApi.sincronizar();
      setMsg({ tipo: "ok", texto: `Sincronizado: ${r.agendas} agendas e ${r.locais} locais.` });
      await carregar();
      setVersaoTotem((v) => v + 1);
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="animate-rise">
      <TotemCard key={versaoTotem} itens={itens} />

      <div className="mt-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Agendas monitoradas</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Usadas só no modo de criação: onde o totem procura o agendamento do paciente (consultórios).
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={sincronizar} disabled={ocupado} className="btn-ghost ring-1 ring-surface-line">
            <IconRefresh className={`h-5 w-5 ${ocupado ? "animate-spin" : ""}`} /> Sincronizar com o SGG
          </button>
          <button onClick={salvar} disabled={!alterado || ocupado} className="btn-primary">
            Salvar alterações
          </button>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-3 text-sm">
        <Stat rotulo="Última sincronização" valor={sync ? dataHora(sync.executado_em) : "…"} tom={sync?.sucesso === false ? "erro" : "ok"} />
        <Stat rotulo="Intervalo" valor={sync ? `${Math.round(sync.intervalo_segundos / 60)} min` : "…"} />
        <Stat rotulo="Modo SGG" valor={sync?.modo_sgg === "http" ? "API real" : "Simulado (fake)"} tom={sync?.modo_sgg === "http" ? "ok" : "aviso"} />
        <Stat rotulo="Monitoradas" valor={String(monitoradas.length)} />
      </div>

      {msg && (
        <p className={`mt-4 rounded-lg px-4 py-3 text-sm font-medium ${msg.tipo === "ok" ? "bg-ok-soft text-ok" : "bg-brand-red-50 text-brand-red"}`}>{msg.texto}</p>
      )}

      <div className="mt-5 overflow-hidden rounded-xl2 bg-white shadow-card ring-1 ring-surface-line">
        <table className="w-full text-sm">
          <thead className="bg-surface-alt text-left text-xs font-semibold uppercase tracking-wider text-ink-soft">
            <tr>
              <th className="px-4 py-3">Monitorar</th>
              <th className="px-4 py-3">Agenda (SGG)</th>
              <th className="px-4 py-3">Local</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-line">
            {carregando && (
              <tr><td colSpan={3} className="px-4 py-10 text-center text-ink-muted">Carregando…</td></tr>
            )}
            {!carregando && itens.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-10 text-center text-ink-muted">Nenhuma agenda. Clique em “Sincronizar com o SGG”.</td></tr>
            )}
            {itens.map((i) => (
              <tr key={i.agenda_id_sgg} className={`${i.monitorada ? "" : "text-ink-muted"} ${i.ativa ? "" : "opacity-50"}`}>
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-brand-blue"
                    checked={i.monitorada}
                    disabled={!i.ativa && !i.monitorada}
                    onChange={(e) => atualizar(i.agenda_id_sgg, { monitorada: e.target.checked })}
                    aria-label={`Monitorar ${i.agenda_nome}`}
                  />
                </td>
                <td className="px-4 py-3 font-semibold text-ink">
                  {i.agenda_nome}
                  <span className={`badge ml-2 ${i.por_ordem_chegada ? "bg-ok-soft text-ok" : "bg-brand-blue-50 text-brand-blue"}`}>
                    {i.por_ordem_chegada ? "ordem de chegada" : "hora marcada"}
                  </span>
                  {!i.ativa && (
                    <span className="badge ml-2 bg-warn-soft text-warn">
                      {i.monitorada ? "removida/inativa no SGG: desmarque e salve" : "inativa"}
                    </span>
                  )}
                  <span className="ml-2 font-mono text-xs text-ink-soft">#{i.agenda_id_sgg}</span>
                </td>
                <td className="px-4 py-3">{i.local_nome ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Stat({ rotulo, valor, tom = "neutro" }: { rotulo: string; valor: string; tom?: "ok" | "erro" | "aviso" | "neutro" }) {
  const cls = { ok: "text-ok", erro: "text-brand-red", aviso: "text-warn", neutro: "text-ink" }[tom];
  return (
    <div className="rounded-lg bg-white px-3 py-2 ring-1 ring-surface-line">
      <span className="text-xs text-ink-soft">{rotulo}: </span>
      <span className={`font-semibold ${cls}`}>{valor}</span>
    </div>
  );
}
