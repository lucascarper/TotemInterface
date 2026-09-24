import type { IdentificarResponse, TipoAtendimento } from "@/api/types";
import { IconCheck } from "@/components/Icons";
import { dataNascimentoBr, hora } from "@/lib/format";

interface Props {
  dados: IdentificarResponse;
  tipo: TipoAtendimento;
  onConfirmar: () => void;
  onCorrigir: () => void;
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string | null }) {
  if (!valor) return null;
  return (
    <div className="flex items-baseline justify-between gap-6 border-b border-surface-line py-2 last:border-0">
      <dt className="text-sm font-medium uppercase tracking-wider text-ink-soft">{rotulo}</dt>
      <dd className="text-right text-lg font-semibold text-ink">{valor}</dd>
    </div>
  );
}

export function ConfirmScreen({ dados, tipo, onConfirmar, onCorrigir }: Props) {
  const { paciente } = dados;
  return (
    <div className="w-full max-w-xl animate-rise">
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight md:text-4xl">Esses dados estão corretos?</h1>
        <p className="mt-1 text-ink-muted">Confira antes de confirmar sua chegada</p>
      </div>

      <div className="mt-5 rounded-xl3 bg-white p-5 shadow-card ring-1 ring-surface-line">
        <div className="flex items-center gap-3">
          <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand-blue-50 text-2xl font-bold text-brand-blue">
            {paciente.nome.split(" ").map((p) => p[0]).slice(0, 2).join("")}
          </div>
          <div>
            <p className="text-2xl font-bold leading-tight">{paciente.nome}</p>
            <p className="text-ink-muted">CPF {paciente.cpf_mascarado}</p>
          </div>
        </div>
        <dl className="mt-4">
          <Linha rotulo="Nascimento" valor={dataNascimentoBr(paciente.data_nascimento)} />
          <Linha rotulo="Telefone" valor={paciente.telefone_mascarado} />
          <Linha rotulo="Atendimento" valor={tipo === "PREFERENCIAL" ? "Preferencial" : "Normal"} />
        </dl>

        <div className={`mt-3 rounded-xl px-4 py-2.5 text-sm font-medium ${dados.possui_agendamento_hoje ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn"}`}>
          {dados.possui_agendamento_hoje
            ? `Agendamento encontrado para hoje${dados.agendamento_horario ? ` às ${hora(dados.agendamento_horario)}` : ""}${dados.agenda_nome ? ` · ${dados.agenda_nome}` : ""}.`
            : "Não encontramos agendamento para hoje. Você será incluído(a) na fila de encaixe."}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-[1fr_2fr]">
        <button onClick={onCorrigir} className="btn-big h-[clamp(2.75rem,8dvh,5rem)] bg-white text-xl !text-ink-muted ring-1 ring-surface-line">
          Não, corrigir CPF
        </button>
        <button onClick={onConfirmar} className="btn-big h-[clamp(2.75rem,8dvh,5rem)] bg-ok text-2xl">
          <IconCheck className="mr-2 h-8 w-8" /> Sim, confirmar chegada
        </button>
      </div>
    </div>
  );
}
