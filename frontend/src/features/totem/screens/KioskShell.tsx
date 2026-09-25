import { useEffect, useState, type ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { IconBack, IconWifiOff } from "@/components/Icons";

interface Props {
  children: ReactNode;
  online: boolean;
  showBack: boolean;
  onBack: () => void;
}

const fmtHora = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });
const fmtData = new Intl.DateTimeFormat("pt-BR", { weekday: "long", day: "numeric", month: "long" });

function Relogio() {
  const [agora, setAgora] = useState(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setAgora(new Date()), 15_000);
    return () => window.clearInterval(id);
  }, []);
  const data = fmtData.format(agora);
  return (
    <div className="text-right leading-tight">
      <p className="text-2xl font-bold tabular-nums text-ink">{fmtHora.format(agora)}</p>
      <p className="hidden whitespace-nowrap text-sm font-medium text-ink-muted sm:block">{data.charAt(0).toUpperCase() + data.slice(1)}</p>
    </div>
  );
}

export function KioskShell({ children, online, showBack, onBack }: Props) {
  return (
    <div className="kiosk flex h-[100dvh] flex-col overflow-hidden bg-surface-alt">
      <header className="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center border-b border-surface-line bg-white px-6 py-[clamp(0.5rem,1.6dvh,1rem)] sm:px-8">
        <div className="justify-self-start">
          {showBack && (
            <button
              onClick={onBack}
              className="-ml-2 flex h-12 items-center gap-1.5 rounded-xl2 px-3 text-lg font-semibold text-brand-blue active:bg-brand-blue-50"
              aria-label="Voltar"
            >
              <IconBack className="h-6 w-6" /> Voltar
            </button>
          )}
        </div>
        <Logo className="h-[clamp(2.25rem,6dvh,3.5rem)]" />
        <div className="flex items-center gap-4 justify-self-end">
          {!online && (
            <span className="badge gap-1.5 bg-brand-red-50 py-1 text-sm text-brand-red">
              <IconWifiOff className="h-4 w-4" /> Sem rede
            </span>
          )}
          <Relogio />
        </div>
      </header>
      <main className="flex min-h-0 flex-1 flex-col items-center justify-center overflow-hidden px-6 py-[clamp(0.75rem,3dvh,2rem)] sm:px-10">
        {children}
      </main>
    </div>
  );
}
