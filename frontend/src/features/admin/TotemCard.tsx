import { useCallback, useEffect, useMemo, useState } from "react";
import { adminApi } from "@/api/admin";
import { ApiError } from "@/api/client";
import type { AgendaResumo, ConfiguracaoAgenda, ModoTotem } from "@/api/types";
import { IconDown, IconTrash, IconUp } from "@/components/Icons";

function tratar(e: unknown): string {
  if (e instanceof ApiError && e.status === 401) window.dispatchEvent(new Event("admin:unauthorized"));
  return e instanceof ApiError ? e.message : "Erro inesperado.";
}

const MODOS: { valor: ModoTotem; titulo: string; descricao: string }[] = [
  {
    valor: "CRIACAO",
    titulo: "Criar registro na recepção",
    descricao: "Cada chegada cria um registro novo numa agenda da recepção, já como Aguardando.",
  },
  {
    valor: "EDICAO",
    titulo: "Marcar o agendamento como Aguardando",
    descricao:
      "O agendamento que o paciente já tem na recepção passa de Agendado para Aguardando. Quem chega sem agendamento vai para a agenda de encaixe.",
  },
];

interface Estado {
  modo: ModoTotem;
  recepcao: string[];
  encaixe: string;
}

export function TotemCard({ itens }: { itens: ConfiguracaoAgenda[] }) {
  const [estado, setEstado] = useState<Estado>({ modo: "CRIACAO", recepcao: [], encaixe: "" });
  const [salvo, setSalvo] = useState<string>("");
  const [nomesSalvos, setNomesSalvos] = useState<Record<string, AgendaResumo>>({});
  const [adicionar, setAdicionar] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [ocupado, setOcupado] = useState(false);
  const [msg, setMsg] = useState<{ tipo: "ok" | "erro"; texto: string } | null>(null);

  const carregar = useCallback(async () => {
    setCarregando(true);
    try {
      const cfg = await adminApi.totem();
      const novo: Estado = {
        modo: cfg.modo,
        recepcao: cfg.agendas_recepcao.map((a) => a.agenda_id_sgg),
        encaixe: cfg.agenda_encaixe?.agenda_id_sgg ?? "",
      };
      const nomes: Record<string, AgendaResumo> = {};
      for (const a of [...cfg.agendas_recepcao, ...(cfg.agenda_encaixe ? [cfg.agenda_encaixe] : [])]) nomes[a.agenda_id_sgg] = a;
      setEstado(novo);
      setSalvo(JSON.stringify(novo));
      setNomesSalvos(nomes);
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const porId = useMemo(() => Object.fromEntries(itens.map((i) => [i.agenda_id_sgg, i])), [itens]);
  const agenda = (id: string) => {
    const i = porId[id];
    if (i) return { nome: i.agenda_nome, ativa: i.ativa, ordem: i.por_ordem_chegada };
    const s = nomesSalvos[id];
    return { nome: s?.agenda_nome ?? id, ativa: s?.ativa ?? false, ordem: s?.por_ordem_chegada ?? false };
  };

  const ativas = itens.filter((i) => i.ativa);
  const paraAdicionar = ativas.filter((i) => !estado.recepcao.includes(i.agenda_id_sgg) && i.agenda_id_sgg !== estado.encaixe);
  const paraEncaixe = ativas.filter((i) => i.por_ordem_chegada && !estado.recepcao.includes(i.agenda_id_sgg));

  const alterado = JSON.stringify(estado) !== salvo;
  const edicao = estado.modo === "EDICAO";
  const faltaEncaixe = edicao && !estado.encaixe;

  const mover = (i: number, delta: number) =>
    setEstado((s) => {
      const r = [...s.recepcao];
      [r[i], r[i + delta]] = [r[i + delta], r[i]];
      return { ...s, recepcao: r };
    });
  const remover = (id: string) => setEstado((s) => ({ ...s, recepcao: s.recepcao.filter((x) => x !== id) }));
  const incluir = () => {
    if (!adicionar) return;
    setEstado((s) => ({ ...s, recepcao: [...s.recepcao, adicionar] }));
    setAdicionar("");
  };

  const salvar = async () => {
    setOcupado(true);
    setMsg(null);
    try {
      await adminApi.salvarTotem(estado.modo, estado.recepcao, estado.encaixe || null);
      setMsg({ tipo: "ok", texto: "Configuração do totem salva. Vale a partir do próximo check-in." });
      await carregar();
    } catch (e) {
      setMsg({ tipo: "erro", texto: tratar(e) });
    } finally {
      setOcupado(false);
    }
  };

  return (
    <div className="rounded-xl2 bg-white p-5 shadow-card ring-1 ring-surface-line">
      <h2 className="text-lg font-bold">Modo do totem</h2>
      <p className="mt-1 text-sm text-ink-muted">Como o totem registra a chegada do paciente no SGG.</p>

      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2" role="radiogroup" aria-label="Modo do totem">
        {MODOS.map((m) => {
          const ativo = estado.modo === m.valor;
          return (
            <button
              key={m.valor}
              type="button"
              role="radio"
              aria-checked={ativo}
              disabled={carregando}
              onClick={() => setEstado((s) => ({ ...s, modo: m.valor }))}
              className={`rounded-xl p-4 text-left ring-1 transition ${ativo ? "bg-brand-blue-50 ring-2 ring-brand-blue" : "bg-white ring-surface-line hover:bg-surface-alt"}`}
            >
              <span className="flex items-center gap-2 font-semibold text-ink">
                <span className={`grid h-4 w-4 place-items-center rounded-full ring-2 ${ativo ? "ring-brand-blue" : "ring-ink-soft"}`}>
                  {ativo && <span className="h-2 w-2 rounded-full bg-brand-blue" />}
                </span>
                {m.titulo}
              </span>
              <span className="mt-1 block text-sm text-ink-muted">{m.descricao}</span>
            </button>
          );
        })}
      </div>

      <h3 className="mt-6 font-bold">Agendas da recepção</h3>
      <p className="mt-1 text-sm text-ink-muted">
        {edicao
          ? "Onde o totem procura o agendamento do paciente para marcar como Aguardando (o primeiro do dia)."
          : "Onde o registro de chegada é criado. O Preferencial vai para a 1ª; o Normal, para a de menor fila."}
      </p>
      <ol className="mt-3 divide-y divide-surface-line rounded-xl ring-1 ring-surface-line">
        {estado.recepcao.length === 0 && (
          <li className="px-4 py-3 text-sm text-ink-muted">{carregando ? "Carregando…" : "Nenhuma agenda da recepção."}</li>
        )}
        {estado.recepcao.map((id, i) => {
          const a = agenda(id);
          return (
            <li key={id} className="flex items-center gap-3 px-4 py-2.5">
              <span className="w-6 text-sm font-bold tabular-nums text-ink-muted">{i + 1}º</span>
              <span className="flex-1 font-semibold text-ink">
                {a.nome}
                <span className={`badge ml-2 ${a.ordem ? "bg-ok-soft text-ok" : "bg-brand-blue-50 text-brand-blue"}`}>
                  {a.ordem ? "ordem de chegada" : "hora marcada"}
                </span>
                {!a.ativa && <span className="badge ml-2 bg-warn-soft text-warn">inativa no SGG: remova e salve</span>}
              </span>
              <button type="button" className="btn-ghost p-2" onClick={() => mover(i, -1)} disabled={i === 0} aria-label={`Subir ${a.nome}`}>
                <IconUp className="h-4 w-4" />
              </button>
              <button type="button" className="btn-ghost p-2" onClick={() => mover(i, 1)} disabled={i === estado.recepcao.length - 1} aria-label={`Descer ${a.nome}`}>
                <IconDown className="h-4 w-4" />
              </button>
              <button type="button" className="btn-ghost p-2 !text-brand-red hover:!bg-brand-red-50" onClick={() => remover(id)} aria-label={`Remover ${a.nome}`}>
                <IconTrash className="h-4 w-4" />
              </button>
            </li>
          );
        })}
      </ol>
      <div className="mt-3 flex flex-wrap gap-2">
        <select className="field max-w-sm flex-1" value={adicionar} onChange={(e) => setAdicionar(e.target.value)} disabled={carregando} aria-label="Agenda para adicionar à recepção">
          <option value="">Adicionar agenda da recepção…</option>
          {paraAdicionar.map((o) => (
            <option key={o.agenda_id_sgg} value={o.agenda_id_sgg}>
              {o.agenda_nome} ({o.por_ordem_chegada ? "ordem de chegada" : "hora marcada"})
            </option>
          ))}
        </select>
        <button type="button" className="btn-ghost ring-1 ring-surface-line" onClick={incluir} disabled={!adicionar}>
          Adicionar
        </button>
      </div>

      <div className={`mt-6 rounded-xl p-4 ring-1 ${edicao ? "bg-surface-alt ring-brand-blue" : "ring-surface-line"}`}>
        <h3 className="font-bold">Agenda de encaixe</h3>
        <p className="mt-1 text-sm text-ink-muted">
          Usada só no modo de edição: quem chega sem agendamento Agendado na recepção é incluído aqui, já como Aguardando.
          Precisa ser por ordem de chegada.
        </p>
        <select
          className="field mt-3 max-w-sm"
          value={estado.encaixe}
          onChange={(e) => setEstado((s) => ({ ...s, encaixe: e.target.value }))}
          disabled={carregando}
          aria-label="Agenda de encaixe"
        >
          <option value="">— nenhuma —</option>
          {estado.encaixe && !paraEncaixe.some((o) => o.agenda_id_sgg === estado.encaixe) && (
            <option value={estado.encaixe}>{agenda(estado.encaixe).nome} (inativa)</option>
          )}
          {paraEncaixe.map((o) => (
            <option key={o.agenda_id_sgg} value={o.agenda_id_sgg}>
              {o.agenda_nome}
            </option>
          ))}
        </select>
        {faltaEncaixe && (
          <p className="mt-2 text-sm font-medium text-warn">Escolha a agenda de encaixe para poder salvar o modo de edição.</p>
        )}
      </div>

      {msg && (
        <p className={`mt-4 rounded-lg px-4 py-3 text-sm font-medium ${msg.tipo === "ok" ? "bg-ok-soft text-ok" : "bg-brand-red-50 text-brand-red"}`}>{msg.texto}</p>
      )}

      <button onClick={salvar} disabled={!alterado || ocupado || faltaEncaixe} className="btn-primary mt-4">
        Salvar configuração do totem
      </button>
    </div>
  );
}
