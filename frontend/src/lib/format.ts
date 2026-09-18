const fmtHora = new Intl.DateTimeFormat("pt-BR", { hour: "2-digit", minute: "2-digit" });
const fmtDataHora = new Intl.DateTimeFormat("pt-BR", { dateStyle: "short", timeStyle: "medium" });

export const hora = (iso: string | null | undefined) => (iso ? fmtHora.format(new Date(iso)) : "");
export const dataHora = (iso: string | null | undefined) => (iso ? fmtDataHora.format(new Date(iso)) : "—");

export function dataNascimentoBr(iso: string | null): string | null {
  if (!iso) return null;
  const [y, m, d] = iso.split("-");
  return y && m && d ? `${d}/${m}/${y}` : iso;
}
