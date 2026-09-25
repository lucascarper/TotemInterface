import type { CheckinResponse } from "@/api/types";
import { IconCheck } from "@/components/Icons";
import { hora } from "@/lib/format";
import { Countdown } from "./Countdown";

export function SuccessScreen({ resultado, segundos }: { resultado: CheckinResponse; segundos: number }) {
  const encaixe = resultado.resultado === "ENCAIXE_CRIADO";
  return (
    <div className="flex w-full max-w-2xl animate-rise flex-col items-center text-center">
      <span className="grid h-[clamp(4.5rem,15dvh,6rem)] w-[clamp(4.5rem,15dvh,6rem)] animate-pop place-items-center rounded-full bg-ok text-white shadow-soft">
        <IconCheck className="h-1/2 w-1/2" />
      </span>
      <h1 className="mt-[clamp(0.75rem,3dvh,1.5rem)] text-[clamp(2rem,6.5dvh,3rem)] font-bold leading-tight tracking-tight">
        Chegada confirmada!
      </h1>
      <p className="mt-2 max-w-[40ch] text-xl leading-snug text-ink-muted">
        {resultado.paciente_nome}, aguarde na recepção. Você será chamado(a) em breve.
      </p>

      <dl className="panel mt-[clamp(1rem,3.5dvh,2rem)] grid w-full max-w-lg grid-cols-2 divide-x divide-surface-line text-left">
        <div className="px-5 py-4">
          <dt className="text-sm font-medium text-ink-muted">{encaixe ? "Incluído(a) em" : "Agendamento"}</dt>
          <dd className="mt-0.5 truncate text-xl font-bold text-brand-blue">{resultado.agenda_nome}</dd>
        </div>
        <div className="px-5 py-4">
          <dt className="text-sm font-medium text-ink-muted">{encaixe ? "Chegada às" : "Horário"}</dt>
          <dd className="mt-0.5 text-xl font-bold tabular-nums text-ink">
            {hora(resultado.horario)}
            <span className="ml-2 text-base font-semibold text-ink-muted">
              {resultado.tipo_atendimento === "PREFERENCIAL" ? "Preferencial" : "Normal"}
            </span>
          </dd>
        </div>
      </dl>

      <Countdown segundos={segundos} />
    </div>
  );
}
