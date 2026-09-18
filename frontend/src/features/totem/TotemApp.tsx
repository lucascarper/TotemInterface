import { useCallback, useEffect, useReducer } from "react";
import { ApiError } from "@/api/client";
import { totemApi } from "@/api/totem";
import { useIdleReset } from "@/hooks/useIdleReset";
import { useOnline } from "@/hooks/useOnline";
import { cpfValido } from "@/lib/cpf";
import { inicial, reducer } from "./machine";
import { KioskShell } from "./screens/KioskShell";
import { HomeScreen } from "./screens/HomeScreen";
import { CpfScreen } from "./screens/CpfScreen";
import { ConfirmScreen } from "./screens/ConfirmScreen";
import { SuccessScreen } from "./screens/SuccessScreen";
import { ErrorScreen } from "./screens/ErrorScreen";
import { LoadingScreen } from "./screens/LoadingScreen";

const RESET_SECONDS = Number(import.meta.env.VITE_IDLE_RESET_SECONDS ?? 8);
const IDLE_SECONDS = 60;

const RETRYABLE = new Set(["SGG_INDISPONIVEL", "SEM_CONEXAO", "ERRO_INTERNO"]);

export default function TotemApp() {
  const [s, dispatch] = useReducer(reducer, inicial);
  const online = useOnline();

  const falhar = useCallback((e: unknown) => {
    const err = e instanceof ApiError ? e : new ApiError(500, "ERRO_INTERNO", "Erro inesperado. Tente novamente.");
    dispatch({ type: "FALHA", codigo: err.codigo, mensagem: err.message, tentarNovamente: RETRYABLE.has(err.codigo) });
  }, []);

  // Efeitos por estado: buscar paciente / confirmar check-in.
  useEffect(() => {
    if (s.tela === "buscando") {
      totemApi.identificar(s.cpf).then((dados) => dispatch({ type: "ENCONTRADO", dados })).catch(falhar);
    } else if (s.tela === "confirmando") {
      totemApi.checkin(s.cpf, s.tipo).then((resultado) => dispatch({ type: "CHECKIN_OK", resultado })).catch(falhar);
    }
  }, [s.tela, falhar]); // eslint-disable-line react-hooks/exhaustive-deps

  // RF11: volta ao início sozinho após sucesso/erro; e após inatividade em qualquer tela.
  const terminal = s.tela === "sucesso" || s.tela === "erro";
  useEffect(() => {
    if (!terminal) return;
    const t = window.setTimeout(() => dispatch({ type: "REINICIAR" }), RESET_SECONDS * 1000);
    return () => window.clearTimeout(t);
  }, [terminal, s]);
  useIdleReset(s.tela === "inicio" ? null : IDLE_SECONDS, () => dispatch({ type: "REINICIAR" }));

  const buscar = () => {
    if (s.tela !== "cpf") return;
    if (!cpfValido(s.cpf)) {
      dispatch({ type: "FALHA", codigo: "CPF_INVALIDO", mensagem: "CPF inválido. Confira os números." });
      return;
    }
    dispatch({ type: "BUSCAR" });
  };

  return (
    <KioskShell online={online} showBack={s.tela === "cpf" || s.tela === "confirmar"} onBack={() => dispatch({ type: "VOLTAR" })}>
      {s.tela === "inicio" && <HomeScreen onEscolher={(tipo) => dispatch({ type: "ESCOLHER_TIPO", tipo })} />}
      {s.tela === "cpf" && (
        <CpfScreen
          tipo={s.tipo}
          cpf={s.cpf}
          erro={s.erro}
          onDigito={(d) => dispatch({ type: "DIGITO", d })}
          onApagar={() => dispatch({ type: "APAGAR" })}
          onLimpar={() => dispatch({ type: "LIMPAR" })}
          onBuscar={buscar}
        />
      )}
      {s.tela === "buscando" && <LoadingScreen titulo="Localizando seu cadastro…" />}
      {s.tela === "confirmar" && (
        <ConfirmScreen dados={s.dados} tipo={s.tipo} onConfirmar={() => dispatch({ type: "CONFIRMAR" })} onCorrigir={() => dispatch({ type: "VOLTAR" })} />
      )}
      {s.tela === "confirmando" && <LoadingScreen titulo="Registrando sua chegada…" />}
      {s.tela === "sucesso" && <SuccessScreen resultado={s.resultado} segundos={RESET_SECONDS} />}
      {s.tela === "erro" && (
        <ErrorScreen
          codigo={s.codigo}
          mensagem={s.mensagem}
          segundos={RESET_SECONDS}
          tentarNovamente={s.tentarNovamente}
          onTentar={() => dispatch({ type: "VOLTAR" })}
          onInicio={() => dispatch({ type: "REINICIAR" })}
        />
      )}
    </KioskShell>
  );
}
