import { useEffect } from "react";
import type { TipoAtendimento } from "@/api/types";
import { IconArrowRight, IconBackspace } from "@/components/Icons";
import { formatarCpf } from "@/lib/cpf";

interface Props {
  tipo: TipoAtendimento;
  cpf: string;
  erro?: string;
  onDigito: (d: string) => void;
  onApagar: () => void;
  onLimpar: () => void;
  onBuscar: () => void;
}

const TECLAS = ["1", "2", "3", "4", "5", "6", "7", "8", "9"];

export function CpfScreen({ tipo, cpf, erro, onDigito, onApagar, onLimpar, onBuscar }: Props) {
  const completo = cpf.length === 11;

  // Suporte a teclado físico / leitor (útil em testes e tablets com teclado).
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) onDigito(e.key);
      else if (e.key === "Backspace") onApagar();
      else if (e.key === "Enter" && completo) onBuscar();
      else if (e.key === "Escape") onLimpar();
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [completo, onDigito, onApagar, onBuscar, onLimpar]);

  const preferencial = tipo === "PREFERENCIAL";
  const tipoCls = preferencial ? "bg-brand-red-50 text-brand-red" : "bg-brand-blue-50 text-brand-blue";
  const anelCpf = erro ? "animate-shake ring-2 ring-brand-red" : completo ? "ring-2 ring-ok" : "ring-1 ring-surface-line";

  return (
    <div className="grid h-full w-full max-w-5xl animate-rise grid-rows-[auto_minmax(0,1fr)] gap-4 md:grid-cols-2 md:grid-rows-1 md:gap-10">
      <div className="flex flex-col justify-center">
        <span className={`badge self-center px-3 py-1 text-sm md:self-start ${tipoCls}`}>
          {preferencial ? "Atendimento preferencial" : "Atendimento normal"}
        </span>
        <h1 className="mt-2 text-center text-[clamp(1.75rem,5.5dvh,2.75rem)] font-bold leading-tight tracking-tight md:text-left">
          Digite seu CPF
        </h1>
        <p className="mt-1 text-center text-lg text-ink-muted md:text-left">Apenas os números</p>

        <div
          className={`mt-[clamp(0.75rem,3dvh,1.75rem)] whitespace-nowrap rounded-xl2 bg-white px-4 py-[clamp(0.5rem,2.2dvh,1.25rem)] text-center font-mono text-[clamp(1.75rem,6dvh,2.5rem)] tracking-[.06em] tabular-nums ${anelCpf}`}
          aria-live="polite"
          aria-label="CPF digitado"
        >
          {cpf ? formatarCpf(cpf) : <span className="text-ink-soft">000.000.000-00</span>}
        </div>
        <p className={`mt-1.5 min-h-6 text-center text-base font-semibold text-brand-red md:text-left ${erro ? "" : "invisible"}`}>{erro ?? "."}</p>

        <button
          onClick={onBuscar}
          disabled={!completo}
          className="btn-big mt-[clamp(0.5rem,2dvh,1.25rem)] hidden h-[clamp(3.25rem,10dvh,4.5rem)] w-full bg-brand-blue text-2xl md:flex"
        >
          Continuar <IconArrowRight className="h-7 w-7" />
        </button>
      </div>

      <div className="flex min-h-0 flex-col gap-3">
        <div className="grid min-h-0 flex-1 grid-cols-3 grid-rows-4 gap-[clamp(0.4rem,1.4dvh,0.75rem)]">
          {TECLAS.map((t) => (
            <button key={t} className="key" onClick={() => onDigito(t)} aria-label={`Dígito ${t}`}>
              {t}
            </button>
          ))}
          <button className="key !text-lg text-ink-muted" onClick={onLimpar} aria-label="Limpar">
            Limpar
          </button>
          <button className="key" onClick={() => onDigito("0")} aria-label="Dígito 0">
            0
          </button>
          <button className="key text-ink-muted" onClick={onApagar} aria-label="Apagar">
            <IconBackspace className="h-9 w-9" />
          </button>
        </div>
        <button
          onClick={onBuscar}
          disabled={!completo}
          className="btn-big h-[clamp(3rem,8dvh,4.5rem)] w-full shrink-0 bg-brand-blue text-2xl md:hidden"
        >
          Continuar <IconArrowRight className="h-7 w-7" />
        </button>
      </div>
    </div>
  );
}
