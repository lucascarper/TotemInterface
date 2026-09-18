import { BrandMark } from "@/components/Logo";
import { Spinner } from "@/components/Spinner";

export function LoadingScreen({ titulo }: { titulo: string }) {
  return (
    <div className="animate-rise text-center" role="status" aria-live="polite">
      <div className="relative mx-auto grid h-32 w-32 place-items-center">
        <Spinner className="absolute inset-0 h-32 w-32" />
        <BrandMark className="h-12" />
      </div>
      <h1 className="mt-6 text-3xl font-bold tracking-tight">{titulo}</h1>
      <p className="mt-2 text-ink-muted">Isso leva apenas alguns segundos</p>
    </div>
  );
}
