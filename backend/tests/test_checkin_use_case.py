import pytest

from app.domain.entities import ResultadoCheckin, StatusAgendamento, TipoAtendimento, TipoOperacao
from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    PacienteNaoEncontradoError,
)

MARIA, JOAO, ANA = "52998224725", "11144477735", "12345678909"


def test_checkin_atualiza_status_quando_ha_agendamento(container_configurado, sgg):
    dto = container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    assert dto.resultado == ResultadoCheckin.STATUS_ATUALIZADO
    assert dto.agendamento_id_sgg == "AG1"
    assert sgg.obter_agendamento("AG1").status == StatusAgendamento.AGUARDANDO
    assert dto.agenda_nome.startswith("Clínico Geral")


def test_checkin_cria_encaixe_quando_nao_ha_agendamento(container_configurado, sgg):
    dto = container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.PREFERENCIAL)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert criado.agenda_id_sgg == "A4"
    assert criado.status == StatusAgendamento.AGUARDANDO
    assert criado.tipo_atendimento == TipoAtendimento.PREFERENCIAL
    assert dto.agenda_nome == "Encaixe Recepção"


def test_checkin_repetido_nao_duplica(container_configurado):
    with pytest.raises(CheckinJaRealizadoError):
        container_configurado.realizar_checkin().executar(ANA, TipoAtendimento.NORMAL)


def test_paciente_nao_cadastrado(container_configurado):
    with pytest.raises(PacienteNaoEncontradoError):
        container_configurado.realizar_checkin().executar("390.533.447-05", TipoAtendimento.NORMAL)


def test_sem_encaixe_configurado(container):
    container.sincronizar().executar()
    from app.domain.entities import ConfiguracaoAgenda

    with container.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", True, None, False)])
        uow.commit()
    with pytest.raises(AgendaEncaixeNaoConfiguradaError):
        container.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)


def test_agenda_nao_monitorada_e_ignorada(container_configurado, sgg):
    """Agendamento em agenda não monitorada não conta: paciente vai para encaixe."""
    from app.domain.entities import ConfiguracaoAgenda

    with container_configurado.uow as uow:
        uow.configuracoes.salvar_todas(
            [
                ConfiguracaoAgenda("A1", False, None, False),
                ConfiguracaoAgenda("A2", True, "A4", True),
            ]
        )
        uow.commit()
    dto = container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    assert sgg.obter_agendamento("AG1").status == StatusAgendamento.AGENDADO


def test_operacoes_sao_auditadas(container_configurado):
    container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    logs = container_configurado.listar_logs().executar()
    tipos = [log.tipo for log in logs]
    assert TipoOperacao.ATUALIZACAO_STATUS in tipos
    assert all(log.cpf_mascarado != MARIA for log in logs if log.cpf_mascarado)
    assert logs[0].cpf_mascarado == "***.982.247-**"


def test_identificar_paciente_informa_agendamento(container_configurado):
    dto = container_configurado.identificar_paciente().executar(MARIA)
    assert dto.possui_agendamento_hoje is True
    assert dto.paciente.nome == "Maria Silva"
    assert dto.paciente.cpf_mascarado == "***.982.247-**"
    assert dto.paciente.telefone_mascarado == "(**) *****-4321"


def test_recusa_do_sgg_e_auditada(container_configurado, sgg):
    from app.domain.exceptions import SggOperacaoRecusadaError

    def recusar(*a, **k):
        raise SggOperacaoRecusadaError("D16026", "Já possui compromisso nesta agenda hoje.")

    sgg.criar_agendamento = recusar
    with pytest.raises(SggOperacaoRecusadaError):
        container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)
    ultimo = container_configurado.listar_logs().executar(1)[0]
    assert ultimo.tipo == TipoOperacao.ERRO and "D16026" in ultimo.mensagem
