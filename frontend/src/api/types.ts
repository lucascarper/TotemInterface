export type TipoAtendimento = "PREFERENCIAL" | "NORMAL";
export type ResultadoCheckin = "STATUS_ATUALIZADO" | "ENCAIXE_CRIADO";

export interface PacientePublico {
  id_sgg: string;
  nome: string;
  cpf_mascarado: string;
  data_nascimento: string | null;
  telefone_mascarado: string | null;
}

export interface IdentificarResponse {
  paciente: PacientePublico;
  possui_agendamento_hoje: boolean;
  agendamento_horario: string | null;
  agenda_nome: string | null;
}

export interface CheckinResponse {
  resultado: ResultadoCheckin;
  paciente_nome: string;
  agendamento_id_sgg: string;
  agenda_nome: string;
  horario: string;
  tipo_atendimento: TipoAtendimento;
}

export interface ConfiguracaoAgenda {
  agenda_id_sgg: string;
  agenda_nome: string;
  local_nome: string | null;
  ativa: boolean;
  por_ordem_chegada: boolean;
  monitorada: boolean;
  agenda_encaixe_id_sgg: string | null;
  encaixe_padrao: boolean;
  incluir_da_unidade: boolean;
}

export interface StatusSincronizacao {
  executado_em: string | null;
  sucesso: boolean | null;
  mensagem: string | null;
  intervalo_segundos: number;
  modo_sgg: "fake" | "http";
}

export interface LogItem {
  id: number;
  criado_em: string;
  tipo: string;
  sucesso: boolean;
  mensagem: string;
  cpf_mascarado: string | null;
  paciente_id_sgg: string | null;
  agendamento_id_sgg: string | null;
  agenda_id_sgg: string | null;
  tipo_atendimento: TipoAtendimento | null;
  detalhes: Record<string, unknown>;
}

export interface ResultadoEncaixeAutomatico {
  simulado: boolean;
  incluidos: {
    funcionario_id_sgg: string;
    agenda_origem_nome: string;
    agenda_encaixe_nome: string;
    agendamento_origem_id_sgg: string;
  }[];
  ja_existiam: number;
  sem_cadastro: number;
  recusados: number;
  adiados: number;
  avisos: string[];
}
