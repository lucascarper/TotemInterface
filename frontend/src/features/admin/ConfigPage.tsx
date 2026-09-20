import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi } from "@/api/admin";
import { ApiError } from "@/api/client";
import type { ConfiguracaoAgenda, ResultadoEncaixeAutomatico, StatusSincronizacao } from "@/api/types";
import { IconRefresh } from "@/components/Icons";
import { dataHora } from "@/lib/format";

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
  const [simulacao, setSimulacao] = useState<ResultadoEncaixeAutomatico | null>(null);

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
  const opcoesEncaixe = useMemo(() => itens.filter((i) => i.ativa), [itens]);
  const problemas = monitoradas.filter((i) => !i.agenda_encaixe_id_sgg);
  const temPadrao = monitoradas.some((i) => i.encaixe_padrao && i.agenda_encaixe_id_sgg);

  const podeIncluirDaUnidade = (i: ConfiguracaoAgenda) =>
    Boolean(itens.find((x) => x.agenda_id_sgg === i.agenda_encaixe_id_sgg)?.por_ordem_chegada);

  const atualizar = (id: string, patch: Partial<ConfiguracaoAgenda>) =>
    setItens((prev) =>
      prev.map((i) => {
        if (i.agenda_id_sgg !== id) return patch.encaixe_padrao ? { ...i, encaixe_padrao: false } : i;
        const novo = { ...i, ...patch };
        if (!novo.monitorada) {
          novo.agenda_encaixe_id_sgg = null;
          novo.encaixe_padrao = false;
        }
        // A inclusão automática só vale com encaixe por ordem de chegada.
        const encaixe = prev.find((x) => x.agenda_id_sgg === novo.agenda_encaixe_id_sgg);
        if (!novo.monitorada || !encaixe?.por_ordem_chegada) novo.incluir_da_unidade = false;
        return novo;
      }),
    );

  const salvar = async () => {
    setOcupado(true);
    setMsg(null);
    try {
      await adminApi.salvar(
        itens.map(
          ({ agenda_id_sgg, monitorada, agenda_encaixe_id_sgg, encaixe_padrao, incluir_da_unidade }) => ({
            agenda_id_sgg,
            monitorada,
            agenda_encaixe_id_sgg,
            encaixe_padrao,
            incluir_da_unidade,
          }),
        ),
      );
      setOriginal(JSON.stringify(itens));
      setMsg({ tipo: "ok", texto: "Configuração salva. O totem já usa as novas regras." });
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setOcupado(false);
    }
  };

  const simular = async () => {
    setOcupado(true);
    setMsg(null);
    setSimulacao(null);
    try {
      setSimulacao(await adminApi.simularEncaixeAutomatico());
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
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="animate-rise">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Agendas do totem</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Marque quais agendas do SGG o totem consulta e, para cada uma, a agenda de encaixe usada quando o paciente não tem horário.
            Prefira agendas por <strong>ordem de chegada</strong> como encaixe: em agendas por hora marcada o totem precisa escolher um horário livre na grade.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={sincronizar} disabled={ocupado} className="btn-ghost ring-1 ring-surface-line">
            <IconRefresh className={`h-5 w-5 ${ocupado ? "animate-spin" : ""}`} /> Sincronizar com o SGG
          </button>
          <button
            onClick={simular}
            disabled={alterado || ocupado || monitoradas.length === 0}
            title={alterado ? "Salve as alterações antes de simular" : undefined}
            className="btn-ghost ring-1 ring-surface-line"
          >
            Simular encaixe automático
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
      {!carregando && monitoradas.length > 0 && problemas.length > 0 && (
        <p className="mt-4 rounded-lg bg-warn-soft px-4 py-3 text-sm font-medium text-warn">
          {problemas.length} agenda(s) monitorada(s) sem agenda de encaixe. Pacientes sem horário usarão o encaixe padrão.
        </p>
      )}
      {!carregando && monitoradas.length > 0 && !temPadrao && (
        <p className="mt-2 rounded-lg bg-warn-soft px-4 py-3 text-sm font-medium text-warn">
          Nenhum encaixe padrão definido. Será usada a primeira agenda monitorada com encaixe configurado.
        </p>
      )}

      {simulacao && (
        <div className="mt-4 rounded-lg bg-brand-blue-50 px-4 py-3 text-sm text-ink">
          <p className="font-semibold text-brand-blue">
            Simulação: {simulacao.incluidos.length} pessoa(s) seriam incluídas agora na agenda de encaixe.
          </p>
          <p className="mt-1 text-ink-muted">
            {simulacao.ja_existiam} já estavam no encaixe · {simulacao.sem_cadastro} sem cadastro para incluir ·
            considera só agendamentos de hoje com status Agendado nas outras agendas da unidade. Nada foi gravado no SGG.
          </p>
          {simulacao.incluidos.length > 0 && (
            <ul className="mt-2 list-inside list-disc text-ink-muted">
              {simulacao.incluidos.slice(0, 8).map((i) => (
                <li key={i.funcionario_id_sgg}>
                  Funcionário #{i.funcionario_id_sgg}: de {i.agenda_origem_nome} para {i.agenda_encaixe_nome}
                </li>
              ))}
              {simulacao.incluidos.length > 8 && <li>e mais {simulacao.incluidos.length - 8}…</li>}
            </ul>
          )}
          {simulacao.avisos.map((a) => (
            <p key={a} className="mt-1 font-medium text-warn">{a}</p>
          ))}
        </div>
      )}

      <div className="mt-5 overflow-hidden rounded-xl2 bg-white shadow-card ring-1 ring-surface-line">
        <table className="w-full text-sm">
          <thead className="bg-surface-alt text-left text-xs font-semibold uppercase tracking-wider text-ink-soft">
            <tr>
              <th className="px-4 py-3">Monitorar</th>
              <th className="px-4 py-3">Agenda (SGG)</th>
              <th className="px-4 py-3">Local</th>
              <th className="px-4 py-3">Agenda de encaixe</th>
              <th className="px-4 py-3 text-center">Encaixe padrão</th>
              <th className="px-4 py-3 text-center" title="Inclui no encaixe, automaticamente, quem tem agendamento hoje nas outras agendas da mesma unidade">
                Incluir da unidade
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-line">
            {carregando && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-ink-muted">Carregando…</td></tr>
            )}
            {!carregando && itens.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-10 text-center text-ink-muted">Nenhuma agenda. Clique em “Sincronizar com o SGG”.</td></tr>
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
                <td className="px-4 py-3">
                  <select
                    className="field py-2"
                    disabled={!i.monitorada}
                    value={i.agenda_encaixe_id_sgg ?? ""}
                    onChange={(e) => atualizar(i.agenda_id_sgg, { agenda_encaixe_id_sgg: e.target.value || null })}
                    aria-label={`Agenda de encaixe para ${i.agenda_nome}`}
                  >
                    <option value="">— selecione —</option>
                    {opcoesEncaixe.map((o) => (
                      <option key={o.agenda_id_sgg} value={o.agenda_id_sgg}>{o.agenda_nome}</option>
                    ))}
                  </select>
                </td>
                <td className="px-4 py-3 text-center">
                  <input
                    type="radio"
                    name="encaixe_padrao"
                    className="h-5 w-5 accent-brand-red"
                    disabled={!i.monitorada || !i.agenda_encaixe_id_sgg}
                    checked={i.encaixe_padrao}
                    onChange={() => atualizar(i.agenda_id_sgg, { encaixe_padrao: true })}
                    aria-label={`Definir ${i.agenda_nome} como encaixe padrão`}
                  />
                </td>
                <td className="px-4 py-3 text-center">
                  <input
                    type="checkbox"
                    className="h-5 w-5 accent-brand-blue"
                    disabled={!i.monitorada || !podeIncluirDaUnidade(i)}
                    checked={i.incluir_da_unidade}
                    onChange={(e) => atualizar(i.agenda_id_sgg, { incluir_da_unidade: e.target.checked })}
                    title={
                      i.monitorada && i.agenda_encaixe_id_sgg && !podeIncluirDaUnidade(i)
                        ? "Só funciona com agenda de encaixe por ordem de chegada"
                        : undefined
                    }
                    aria-label={`Incluir no encaixe os agendamentos da unidade de ${i.agenda_nome}`}
                  />
                </td>
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
