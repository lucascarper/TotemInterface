import { useEffect } from "react";
import type { TipoAtendimento } from "@/api/types";
import { IconBackspace } from "@/components/Icons";
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

  const tipoCls = tipo === "PREFERENCIAL" ? "bg-brand-red-50 text-brand-red" : "bg-brand-blue-50 text-brand-blue";

  return (
    <div className="w-full max-w-lg animate-rise">
      <div className="text-center">
        <span className={`badge ${tipoCls} px-3 py-1 text-sm`}>
          {tipo === "PREFERENCIAL" ? "Atendimento preferencial" : "Atendimento normal"}
        </span>
        <h1 className="mt-4 text-3xl font-bold tracking-tight md:text-4xl">Digite seu CPF</h1>
        <p className="mt-2 text-ink-muted">Apenas os números</p>
      </div>

      <div
        className={`mt-8 whitespace-nowrap rounded-xl2 bg-white px-4 py-5 text-center font-mono text-[2.1rem] tracking-[.08em] shadow-card ring-2 sm:text-4xl sm:tracking-[.1em] ${
          erro ? "animate-shake ring-brand-red" : completo ? "ring-ok" : "ring-surface-line"
        }`}
        aria-live="polite"
        aria-label="CPF digitado"
      >
        {cpf ? formatarCpf(cpf) : <span className="text-ink-soft">000.000.000-00</span>}
      </div>
      <p className={`mt-2 h-6 text-center text-sm font-medium text-brand-red ${erro ? "" : "invisible"}`}>{erro ?? "•"}</p>

      <div className="mt-4 grid grid-cols-3 gap-3">
        {TECLAS.map((t) => (
          <button key={t} className="key" onClick={() => onDigito(t)} aria-label={`Dígito ${t}`}>
            {t}
          </button>
        ))}
        <button className="key text-lg font-semibold text-ink-muted" onClick={onLimpar} aria-label="Limpar">
          Limpar
        </button>
        <button className="key" onClick={() => onDigito("0")} aria-label="Dígito 0">
          0
        </button>
        <button className="key text-brand-red" onClick={onApagar} aria-label="Apagar">
          <IconBackspace className="h-9 w-9" />
        </button>
      </div>

      <button
        onClick={onBuscar}
        disabled={!completo}
        className="btn-big mt-6 h-20 w-full bg-brand-blue text-2xl disabled:opacity-40 disabled:shadow-none"
      >
        Continuar
      </button>
    </div>
  );
}
