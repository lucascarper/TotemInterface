import type { TipoAtendimento } from "@/api/types";
import { IconStar, IconUser } from "@/components/Icons";

export function HomeScreen({ onEscolher }: { onEscolher: (t: TipoAtendimento) => void }) {
  return (
    <div className="w-full max-w-4xl animate-rise text-center">
      <p className="text-lg font-medium text-brand-blue">Bem-vindo(a) à recepção</p>
      <h1 className="mt-2 text-4xl font-bold tracking-tight text-ink md:text-5xl">
        Toque para confirmar sua chegada
      </h1>
      <p className="mt-3 text-lg text-ink-muted">Escolha o tipo de atendimento para começar</p>

      <div className="mt-12 grid grid-cols-1 gap-6 md:grid-cols-2">
        <button
          onClick={() => onEscolher("PREFERENCIAL")}
          className="btn-big min-h-[15rem] flex-col gap-4 bg-brand-red p-8 text-left"
          aria-label="Atendimento preferencial"
        >
          <span className="pointer-events-none absolute -right-8 -top-8 h-36 w-36 rounded-full bg-white/10" />
          <IconStar className="h-14 w-14" />
          <span className="text-3xl font-bold">Preferencial</span>
          <span className="text-base font-normal text-white/85">
            Gestantes, idosos (60+), pessoas com deficiência, com crianças de colo
          </span>
        </button>

        <button
          onClick={() => onEscolher("NORMAL")}
          className="btn-big min-h-[15rem] flex-col gap-4 bg-brand-blue p-8 text-left"
          aria-label="Atendimento normal"
        >
          <span className="pointer-events-none absolute -right-8 -top-8 h-36 w-36 rounded-full bg-white/10" />
          <IconUser className="h-14 w-14" />
          <span className="text-3xl font-bold">Normal</span>
          <span className="text-base font-normal text-white/85">Atendimento comum, por ordem de chegada</span>
        </button>
      </div>
    </div>
  );
}
