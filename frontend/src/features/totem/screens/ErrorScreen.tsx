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
    <div className="flex w-full max-w-2xl animate-rise flex-col items-center text-center">
      <span className={`grid h-[clamp(4rem,13dvh,5.5rem)] w-[clamp(4rem,13dvh,5.5rem)] animate-pop place-items-center rounded-full ${tom}`}>
        <IconAlert className="h-1/2 w-1/2" />
      </span>
      <h1 className="mt-[clamp(0.75rem,3dvh,1.5rem)] text-[clamp(2rem,6dvh,2.75rem)] font-bold leading-tight tracking-tight">
        {TITULOS[codigo] ?? "Algo deu errado"}
      </h1>
      <p className="mt-2 max-w-[42ch] text-xl leading-snug text-ink-muted">{mensagem}</p>

      {recepcao && (
        <p className="panel mt-[clamp(0.75rem,3dvh,1.5rem)] max-w-md px-6 py-3 text-lg font-semibold text-brand-blue">
          Por favor, dirija-se ao balcão da recepção para ser atendido(a).
        </p>
      )}

      <div className="mt-[clamp(1rem,3.5dvh,2rem)] flex w-full max-w-lg justify-center gap-4">
        {tentarNovamente && (
          <button onClick={onTentar} className="btn-big h-[clamp(3rem,9dvh,4rem)] flex-1 bg-brand-blue px-6 text-xl">
            Tentar novamente
          </button>
        )}
        <button onClick={onInicio} className="btn-outline h-[clamp(3rem,9dvh,4rem)] flex-1 px-6 text-xl text-ink-muted">
          Voltar ao início
        </button>
      </div>
      <Countdown segundos={segundos} />
    </div>
  );
}
