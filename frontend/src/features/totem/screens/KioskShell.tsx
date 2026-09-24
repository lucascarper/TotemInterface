import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { IconBack, IconWifiOff } from "@/components/Icons";

interface Props {
  children: ReactNode;
  online: boolean;
  showBack: boolean;
  onBack: () => void;
}

export function KioskShell({ children, online, showBack, onBack }: Props) {
  return (
    <div className="kiosk brand-arc flex h-[100dvh] flex-col overflow-hidden">
      <header className="flex shrink-0 items-center justify-between px-6 pt-[clamp(0.5rem,2.5dvh,1.75rem)] pb-2 sm:px-8">
        <div className="w-20 sm:w-28">
          {showBack && (
            <button onClick={onBack} className="btn-ghost -ml-3 text-lg" aria-label="Voltar">
              <IconBack className="h-7 w-7" /> Voltar
            </button>
          )}
        </div>
        <Logo className="h-[clamp(2.25rem,6dvh,4rem)]" />
        <div className="flex w-20 justify-end sm:w-28">
          {!online && (
            <span className="badge bg-brand-red-50 text-brand-red gap-1.5 py-1">
              <IconWifiOff className="h-4 w-4" /> Sem rede
            </span>
          )}
        </div>
      </header>
      <main className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-hidden px-6 pb-[clamp(0.5rem,2dvh,1.5rem)]">
        {children}
      </main>
      <footer className="shrink-0 pb-[clamp(0.375rem,1.5dvh,1rem)] text-center text-[10px] font-medium tracking-[.18em] text-ink-soft sm:text-xs">
        SAÚDE E SEGURANÇA DO TRABALHO
      </footer>
    </div>
  );
}
