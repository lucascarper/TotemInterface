import type { CheckinResponse } from "@/api/types";
import { IconCheck } from "@/components/Icons";
import { hora } from "@/lib/format";
import { Countdown } from "./Countdown";

export function SuccessScreen({ resultado, segundos }: { resultado: CheckinResponse; segundos: number }) {
  const encaixe = resultado.resultado === "ENCAIXE_CRIADO";
  return (
    <div className="w-full max-w-xl animate-rise text-center">
      <div className="relative mx-auto grid h-24 w-24 place-items-center">
        <span className="absolute inset-0 animate-pulseRing rounded-full bg-ok/25" />
        <span className="grid h-20 w-20 animate-pop place-items-center rounded-full bg-ok text-white shadow-card">
          <IconCheck className="h-12 w-12" />
        </span>
      </div>
      <h1 className="mt-4 text-4xl font-bold tracking-tight">Chegada confirmada!</h1>
      <p className="mt-2 text-xl text-ink-muted">
        {resultado.paciente_nome}, aguarde na recepção. Você será chamado(a) em breve.
      </p>

      <div className="mx-auto mt-5 inline-flex flex-col gap-1 rounded-xl2 bg-white px-8 py-4 text-left shadow-card ring-1 ring-surface-line">
        <span className="text-xs font-semibold uppercase tracking-wider text-ink-soft">
          {encaixe ? "Incluído(a) na agenda de encaixe" : "Agendamento confirmado"}
        </span>
        <span className="text-xl font-bold text-brand-blue">{resultado.agenda_nome}</span>
        <span className="text-ink-muted">
          {encaixe ? "Chegada registrada às" : "Horário"} {hora(resultado.horario)} ·{" "}
          {resultado.tipo_atendimento === "PREFERENCIAL" ? "Preferencial" : "Normal"}
        </span>
      </div>

      <Countdown segundos={segundos} />
    </div>
  );
}
