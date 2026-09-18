/** Máquina de estados do fluxo do totem (RF04→RF11). Pura: sem efeitos. */
import type { CheckinResponse, IdentificarResponse, TipoAtendimento } from "@/api/types";

export type Tela =
  | { tela: "inicio" }
  | { tela: "cpf"; tipo: TipoAtendimento; cpf: string; erro?: string }
  | { tela: "buscando"; tipo: TipoAtendimento; cpf: string }
  | { tela: "confirmar"; tipo: TipoAtendimento; cpf: string; dados: IdentificarResponse }
  | { tela: "confirmando"; tipo: TipoAtendimento; cpf: string; dados: IdentificarResponse }
  | { tela: "sucesso"; resultado: CheckinResponse }
  | { tela: "erro"; codigo: string; mensagem: string; tipo?: TipoAtendimento; cpf?: string; tentarNovamente: boolean };

export type Acao =
  | { type: "ESCOLHER_TIPO"; tipo: TipoAtendimento }
  | { type: "DIGITO"; d: string }
  | { type: "APAGAR" }
  | { type: "LIMPAR" }
  | { type: "BUSCAR" }
  | { type: "ENCONTRADO"; dados: IdentificarResponse }
  | { type: "CONFIRMAR" }
  | { type: "CHECKIN_OK"; resultado: CheckinResponse }
  | { type: "FALHA"; codigo: string; mensagem: string; tentarNovamente?: boolean }
  | { type: "VOLTAR" }
  | { type: "REINICIAR" };

export const inicial: Tela = { tela: "inicio" };

export function reducer(s: Tela, a: Acao): Tela {
  switch (a.type) {
    case "REINICIAR":
      return inicial;
    case "ESCOLHER_TIPO":
      return { tela: "cpf", tipo: a.tipo, cpf: "" };
    case "DIGITO":
      if (s.tela !== "cpf" || s.cpf.length >= 11) return s;
      return { ...s, cpf: s.cpf + a.d, erro: undefined };
    case "APAGAR":
      if (s.tela !== "cpf") return s;
      return { ...s, cpf: s.cpf.slice(0, -1), erro: undefined };
    case "LIMPAR":
      if (s.tela !== "cpf") return s;
      return { ...s, cpf: "", erro: undefined };
    case "BUSCAR":
      if (s.tela !== "cpf") return s;
      return { tela: "buscando", tipo: s.tipo, cpf: s.cpf };
    case "ENCONTRADO":
      if (s.tela !== "buscando") return s;
      return { tela: "confirmar", tipo: s.tipo, cpf: s.cpf, dados: a.dados };
    case "CONFIRMAR":
      if (s.tela !== "confirmar") return s;
      return { ...s, tela: "confirmando" };
    case "CHECKIN_OK":
      return { tela: "sucesso", resultado: a.resultado };
    case "FALHA": {
      const emFluxo = s.tela === "cpf" || s.tela === "buscando" || s.tela === "confirmar" || s.tela === "confirmando";
      if (a.codigo === "CPF_INVALIDO" && emFluxo) {
        return { tela: "cpf", tipo: s.tipo, cpf: s.cpf, erro: a.mensagem };
      }
      const ctx = emFluxo ? { tipo: s.tipo, cpf: s.cpf } : {};
      return { tela: "erro", codigo: a.codigo, mensagem: a.mensagem, tentarNovamente: a.tentarNovamente ?? false, ...ctx };
    }
    case "VOLTAR":
      if (s.tela === "cpf") return inicial;
      if (s.tela === "confirmar") return { tela: "cpf", tipo: s.tipo, cpf: s.cpf };
      if (s.tela === "erro" && s.tentarNovamente && s.tipo) return { tela: "cpf", tipo: s.tipo, cpf: s.cpf ?? "" };
      return inicial;
    default:
      return s;
  }
}
