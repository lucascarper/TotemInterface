import type { ComponentType } from "react";
import type { TipoAtendimento } from "@/api/types";
import { IconArrowRight, IconPreferencial, IconUser } from "@/components/Icons";

interface Opcao {
  tipo: TipoAtendimento;
  titulo: string;
  descricao: string;
  Icone: ComponentType<{ className?: string }>;
  cor: { texto: string; fundo: string; solido: string; barra: string };
}

const OPCOES: Opcao[] = [
  {
    tipo: "PREFERENCIAL",
    titulo: "Preferencial",
    descricao: "Gestantes, idosos (60+), pessoas com deficiência e com crianças de colo",
    Icone: IconPreferencial,
    cor: { texto: "text-brand-red", fundo: "bg-brand-red-50", solido: "bg-brand-red", barra: "before:bg-brand-red" },
  },
  {
    tipo: "NORMAL",
    titulo: "Normal",
    descricao: "Atendimento comum, por ordem de chegada",
    Icone: IconUser,
    cor: { texto: "text-brand-blue", fundo: "bg-brand-blue-50", solido: "bg-brand-blue", barra: "before:bg-brand-blue" },
  },
];

export function HomeScreen({ onEscolher }: { onEscolher: (t: TipoAtendimento) => void }) {
  return (
    <div className="flex h-full w-full max-w-5xl flex-col animate-rise">
      <div className="shrink-0 text-center">
        <p className="text-lg font-semibold text-brand-blue">Bem-vindo(a) à recepção</p>
        <h1 className="mt-1 text-[clamp(1.75rem,5.5dvh,3rem)] font-bold leading-tight tracking-tight text-ink">
          Toque para confirmar sua chegada
        </h1>
        <p className="mt-1 text-lg text-ink-muted">Escolha o tipo de atendimento para começar</p>
      </div>

      <div className="mt-[clamp(1rem,4dvh,2.5rem)] grid min-h-0 flex-1 grid-cols-1 gap-5 md:grid-cols-2 md:gap-6">
        {OPCOES.map(({ tipo, titulo, descricao, Icone, cor }) => (
          <button
            key={tipo}
            onClick={() => onEscolher(tipo)}
            aria-label={`Atendimento ${titulo.toLowerCase()}`}
            className={`relative flex min-h-[9rem] flex-col justify-between overflow-hidden rounded-xl2 bg-white p-[clamp(1.25rem,4dvh,2rem)] text-left shadow-soft ring-1 ring-surface-line transition duration-150 ease-out before:absolute before:inset-y-0 before:left-0 before:w-2 active:scale-[.985] active:bg-surface-alt ${cor.barra}`}
          >
            <span className="flex w-full items-start justify-between">
              <span className={`grid h-[clamp(3.5rem,12dvh,5rem)] w-[clamp(3.5rem,12dvh,5rem)] place-items-center rounded-full ${cor.fundo} ${cor.texto}`}>
                <Icone className="h-1/2 w-1/2" />
              </span>
              <span className={`grid h-12 w-12 place-items-center rounded-full text-white ${cor.solido}`}>
                <IconArrowRight className="h-6 w-6" />
              </span>
            </span>
            <span className="mt-4 block">
              <span className={`block text-[clamp(1.875rem,6dvh,2.75rem)] font-bold leading-tight ${cor.texto}`}>{titulo}</span>
              <span className="mt-1 block max-w-[34ch] text-lg leading-snug text-ink-muted">{descricao}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
