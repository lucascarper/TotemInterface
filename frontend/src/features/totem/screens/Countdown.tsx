import type { CSSProperties } from "react";

/** Barra que esvazia no tempo do retorno automático à tela inicial (RF11). */
export function Countdown({ segundos }: { segundos: number }) {
  return (
    <div className="mx-auto mt-[clamp(0.75rem,3dvh,2.5rem)] w-64">
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-line">
        <div className="h-full origin-left animate-drain rounded-full bg-brand-blue" style={{ "--drain-duration": `${segundos}s` } as CSSProperties} />
      </div>
      <p className="mt-2 text-xs font-medium text-ink-soft">Voltando ao início automaticamente</p>
    </div>
  );
}
