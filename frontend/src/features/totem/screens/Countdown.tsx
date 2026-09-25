import type { CSSProperties } from "react";

/** Barra que esvazia no tempo do retorno automático à tela inicial (RF11). */
export function Countdown({ segundos }: { segundos: number }) {
  return (
    <div className="mx-auto mt-[clamp(0.75rem,3dvh,2rem)] flex flex-col items-center">
      <div className="h-1 w-56 overflow-hidden rounded-full bg-surface-line">
        <div className="h-full origin-left animate-drain rounded-full bg-brand-blue" style={{ "--drain-duration": `${segundos}s` } as CSSProperties} />
      </div>
      <p className="mt-2 text-sm font-medium text-ink-muted">Voltando ao início automaticamente</p>
    </div>
  );
}
