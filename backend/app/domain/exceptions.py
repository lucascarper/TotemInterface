class DomainError(Exception):
    """Erro de regra de negócio. Mensagens são seguras para exibição ao usuário."""

    codigo = "ERRO_DOMINIO"

    def __init__(self, mensagem: str | None = None) -> None:
        super().__init__(mensagem or self.__doc__ or self.codigo)
        self.mensagem = mensagem or (self.__doc__ or self.codigo)


class CpfInvalidoError(DomainError):
    """CPF inválido. Verifique os números e tente novamente."""

    codigo = "CPF_INVALIDO"


class PacienteNaoEncontradoError(DomainError):
    """Não localizamos seu cadastro. Por favor, dirija-se à recepção."""

    codigo = "PACIENTE_NAO_ENCONTRADO"


class AgendaEncaixeNaoConfiguradaError(DomainError):
    """Não foi possível registrar sua chegada. Por favor, dirija-se à recepção."""

    codigo = "ENCAIXE_NAO_CONFIGURADO"


class CheckinJaRealizadoError(DomainError):
    """Sua chegada já foi registrada. Aguarde ser chamado."""

    codigo = "CHECKIN_JA_REALIZADO"


class SggIndisponivelError(DomainError):
    """Sistema temporariamente indisponível. Tente novamente em instantes."""

    codigo = "SGG_INDISPONIVEL"


class ConfiguracaoInvalidaError(DomainError):
    """Configuração inválida."""

    codigo = "CONFIGURACAO_INVALIDA"


class SggOperacaoRecusadaError(DomainError):
    """Não foi possível registrar sua chegada. Por favor, dirija-se à recepção."""

    codigo = "SGG_RECUSOU"

    def __init__(self, codigo_sgg: str, msg_sgg: str) -> None:
        super().__init__()
        self.codigo_sgg = codigo_sgg
        self.msg_sgg = msg_sgg

    def __str__(self) -> str:
        return f"{self.codigo_sgg}: {self.msg_sgg}"
