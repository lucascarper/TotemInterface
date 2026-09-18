import { IconAlert } from "@/components/Icons";
import { Countdown } from "./Countdown";

interface Props {
  codigo: string;
  mensagem: string;
  segundos: number;
  tentarNovamente: boolean;
  onTentar: () => void;
  onInicio: () => void;
}

const TITULOS: Record<string, string> = {
  PACIENTE_NAO_ENCONTRADO: "Cadastro não localizado",
  CHECKIN_JA_REALIZADO: "Chegada já registrada",
  ENCAIXE_NAO_CONFIGURADO: "Não foi possível registrar",
  SGG_RECUSOU: "Não foi possível registrar",
  SGG_INDISPONIVEL: "Sistema indisponível",
  SEM_CONEXAO: "Sem conexão",
};

export function ErrorScreen({ codigo, mensagem, segundos, tentarNovamente, onTentar, onInicio }: Props) {
  const recepcao = ["PACIENTE_NAO_ENCONTRADO", "ENCAIXE_NAO_CONFIGURADO", "SGG_RECUSOU"].includes(codigo);
  const info = codigo === "CHECKIN_JA_REALIZADO";
  const tom = info ? "bg-brand-blue-50 text-brand-blue" : "bg-brand-red-50 text-brand-red";

  return (
    <div className="w-full max-w-xl animate-rise text-center">
      <div className={`mx-auto grid h-28 w-28 animate-pop place-items-center rounded-full ${tom}`}>
        <IconAlert className="h-14 w-14" />
      </div>
      <h1 className="mt-6 text-4xl font-bold tracking-tight">{TITULOS[codigo] ?? "Algo deu errado"}</h1>
      <p className="mt-3 text-xl text-ink-muted">{mensagem}</p>

      {recepcao && (
        <div className="mx-auto mt-6 max-w-md rounded-xl2 bg-white px-6 py-4 text-lg font-semibold text-brand-blue shadow-card ring-1 ring-surface-line">
          Por favor, dirija-se ao balcão da recepção para ser atendido(a).
        </div>
      )}

      <div className="mt-8 flex justify-center gap-4">
        {tentarNovamente && (
          <button onClick={onTentar} className="btn-big h-16 bg-brand-blue px-8 text-xl">
            Tentar novamente
          </button>
        )}
        <button onClick={onInicio} className="btn-big h-16 bg-white px-8 text-xl !text-ink-muted ring-1 ring-surface-line">
          Voltar ao início
        </button>
      </div>
      <Countdown segundos={segundos} />
    </div>
  );
}
