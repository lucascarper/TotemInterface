import { BrandMark } from "@/components/Logo";
import { Spinner } from "@/components/Spinner";

export function LoadingScreen({ titulo }: { titulo: string }) {
  return (
    <div className="flex animate-rise flex-col items-center text-center" role="status" aria-live="polite">
      <div className="relative grid h-28 w-28 place-items-center">
        <Spinner className="absolute inset-0 h-28 w-28" />
        <BrandMark className="h-10" />
      </div>
      <h1 className="mt-6 text-[clamp(1.75rem,5dvh,2.25rem)] font-bold tracking-tight">{titulo}</h1>
      <p className="mt-1 text-lg text-ink-muted">Isso leva apenas alguns segundos</p>
    </div>
  );
}
