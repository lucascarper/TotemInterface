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
    <div className="flex items-baseline justify-between gap-6 py-[clamp(0.4rem,1.4dvh,0.75rem)]">
      <dt className="text-base font-medium text-ink-muted">{rotulo}</dt>
      <dd className="text-right text-xl font-semibold text-ink">{valor}</dd>
    </div>
  );
}

export function ConfirmScreen({ dados, tipo, onConfirmar, onCorrigir }: Props) {
  const { paciente } = dados;
  const iniciais = paciente.nome.split(" ").map((p) => p[0]).slice(0, 2).join("");
  const agendado = dados.possui_agendamento_hoje;

  return (
    <div className="w-full max-w-5xl animate-rise">
      <div className="text-center md:text-left">
        <h1 className="text-[clamp(1.75rem,5.5dvh,2.75rem)] font-bold leading-tight tracking-tight">
          Esses dados estão corretos?
        </h1>
        <p className="mt-1 text-lg text-ink-muted">Confira antes de confirmar sua chegada</p>
      </div>

      <div className="mt-[clamp(0.75rem,3dvh,1.75rem)] grid grid-cols-1 gap-4 md:grid-cols-[1.25fr_1fr] md:gap-6">
        <div className="panel p-[clamp(1rem,3dvh,1.5rem)]">
          <div className="flex items-center gap-4">
            <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand-blue-50 text-xl font-bold text-brand-blue">
              {iniciais}
            </div>
            <div className="min-w-0">
              <p className="truncate text-2xl font-bold leading-tight">{paciente.nome}</p>
              <p className="text-lg text-ink-muted tabular-nums">CPF {paciente.cpf_mascarado}</p>
            </div>
          </div>
          <dl className="mt-[clamp(0.5rem,2dvh,1rem)] divide-y divide-surface-line border-t border-surface-line">
            <Linha rotulo="Nascimento" valor={dataNascimentoBr(paciente.data_nascimento)} />
            <Linha rotulo="Telefone" valor={paciente.telefone_mascarado} />
            <Linha rotulo="Atendimento" valor={tipo === "PREFERENCIAL" ? "Preferencial" : "Normal"} />
          </dl>
        </div>

        <div className="flex flex-col gap-3 md:gap-4">
          <div className={`rounded-xl2 px-5 py-4 ${agendado ? "bg-ok-soft text-ok" : "bg-warn-soft text-warn"}`}>
            <p className="text-lg font-bold">{agendado ? "Agendamento encontrado" : "Sem agendamento hoje"}</p>
            <p className="mt-0.5 text-base font-medium leading-snug">
              {agendado
                ? `Hoje${dados.agendamento_horario ? ` às ${hora(dados.agendamento_horario)}` : ""}${dados.agenda_nome ? `, ${dados.agenda_nome}` : ""}.`
                : "Você será incluído(a) na fila de encaixe."}
            </p>
          </div>
          <button onClick={onConfirmar} className="btn-big h-[clamp(3.25rem,11dvh,5rem)] bg-brand-blue text-2xl md:mt-auto">
            <IconCheck className="h-7 w-7" /> Sim, confirmar chegada
          </button>
          <button onClick={onCorrigir} className="btn-outline h-[clamp(2.75rem,8dvh,4rem)] text-xl text-ink-muted">
            Não, corrigir CPF
          </button>
        </div>
      </div>
    </div>
  );
}
