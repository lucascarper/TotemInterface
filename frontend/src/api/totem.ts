import { request } from "./client";
import type { CheckinResponse, IdentificarResponse, TipoAtendimento } from "./types";

const headers = (): Record<string, string> => {
  const key = import.meta.env.VITE_TOTEM_API_KEY;
  return key ? { "X-Totem-Key": key } : {};
};

export const totemApi = {
  identificar: (cpf: string) =>
    request<IdentificarResponse>("/totem/identificar", { method: "POST", body: { cpf }, headers: headers() }),
  checkin: (cpf: string, tipo_atendimento: TipoAtendimento) =>
    request<CheckinResponse>("/totem/checkin", {
      method: "POST",
      body: { cpf, tipo_atendimento },
      headers: headers(),
    }),
};
