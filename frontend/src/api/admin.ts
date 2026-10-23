import { request } from "./client";
import type { ConfiguracaoAgenda, ConfiguracaoTotem, LogItem, ModoTotem, StatusSincronizacao } from "./types";

const TOKEN_KEY = "totem.admin.token";

export const adminSession = {
  get: () => sessionStorage.getItem(TOKEN_KEY),
  set: (t: string) => sessionStorage.setItem(TOKEN_KEY, t),
  clear: () => sessionStorage.removeItem(TOKEN_KEY),
};

const auth = () => ({ Authorization: `Bearer ${adminSession.get() ?? ""}` });

export interface ConfiguracaoEntrada {
  agenda_id_sgg: string;
  monitorada: boolean;
}

export const adminApi = {
  login: (username: string, password: string) =>
    request<{ access_token: string }>("/admin/login", { method: "POST", body: { username, password } }),
  configuracoes: () => request<ConfiguracaoAgenda[]>("/admin/configuracoes", { headers: auth() }),
  salvar: (configuracoes: ConfiguracaoEntrada[]) =>
    request<void>("/admin/configuracoes", { method: "PUT", body: { configuracoes }, headers: auth() }),
  totem: () => request<ConfiguracaoTotem>("/admin/totem", { headers: auth() }),
  salvarTotem: (modo: ModoTotem, agendas_recepcao: string[], agenda_encaixe_id_sgg: string | null) =>
    request<void>("/admin/totem", {
      method: "PUT",
      body: { modo, agendas_recepcao, agenda_encaixe_id_sgg },
      headers: auth(),
    }),
  manutencao: () => request<{ retencao_logs_dias: number }>("/admin/manutencao", { headers: auth() }),
  sincronizar: () =>
    request<{ agendas: number; locais: number }>("/admin/sincronizar", { method: "POST", headers: auth() }),
  statusSincronizacao: () => request<StatusSincronizacao>("/admin/sincronizacao", { headers: auth() }),
  logs: (limite = 100) => request<LogItem[]>(`/admin/logs?limite=${limite}`, { headers: auth() }),
};
