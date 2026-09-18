/** Cliente HTTP mínimo com erros tipados (código + mensagem vindos da API). */

export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly codigo: string,
    mensagem: string,
  ) {
    super(mensagem);
  }
  get offline() {
    return this.status === 0;
  }
}

interface Options {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  headers?: Record<string, string>;
  timeoutMs?: number;
}

export async function request<T>(path: string, opts: Options = {}): Promise<T> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeoutMs ?? 15000);
  let resp: Response;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      method: opts.method ?? "GET",
      headers: { "Content-Type": "application/json", ...(opts.headers ?? {}) },
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      signal: ctrl.signal,
    });
  } catch {
    clearTimeout(timer);
    throw new ApiError(0, "SEM_CONEXAO", "Sem conexão com o servidor. Tente novamente.");
  }
  clearTimeout(timer);

  if (resp.status === 204) return undefined as T;
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const codigo = data?.codigo ?? (resp.status === 401 ? "NAO_AUTORIZADO" : "ERRO");
    const msg = data?.mensagem ?? data?.detail ?? "Ocorreu um erro. Tente novamente.";
    throw new ApiError(resp.status, codigo, typeof msg === "string" ? msg : JSON.stringify(msg));
  }
  return data as T;
}
