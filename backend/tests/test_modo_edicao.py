"""Modo de edição: marca o agendamento da recepção como Aguardando em vez de criar um novo."""

from datetime import datetime, time

import pytest

from app.domain.entities import (
    Agendamento,
    ModoTotem,
    ResultadoCheckin,
    StatusAgendamento,
    TipoAtendimento,
    TipoOperacao,
)
from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    EmpresaInativaError,
)
from app.infrastructure.clock import TZ

from .conftest import HOJE

MARIA, JOAO, CARLOS_EMPRESA_INATIVA = "52998224725", "11144477735", "86288366757"
ENCAIXE = "A7"


def marcado_na_recepcao(sgg, id_sgg, paciente, agenda, hora, status=StatusAgendamento.AGENDADO):
    sgg.adicionar_agendamento(
        Agendamento(id_sgg, paciente, agenda, datetime.combine(HOJE, hora, TZ), status)
    )


@pytest.fixture
def edicao(container_configurado):
    container_configurado.salvar_totem().executar(ModoTotem.EDICAO, ["A4", "A6"], ENCAIXE, "admin")
    return container_configurado


def checkin(container, cpf, tipo=TipoAtendimento.NORMAL):
    return container.realizar_checkin().executar(cpf, tipo)


def test_marca_o_agendamento_da_recepcao_como_aguardando_sem_criar(edicao, sgg):
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0))
    antes = sgg.ids_agendamentos()

    dto = checkin(edicao, MARIA)

    assert sgg.ids_agendamentos() == antes  # nada criado
    assert sgg.obter_agendamento("R1").status == StatusAgendamento.AGUARDANDO
    assert sgg.obter_agendamento("AG1").status == StatusAgendamento.AGENDADO  # consultório intacto
    assert dto.resultado == ResultadoCheckin.AGENDAMENTO_CONFIRMADO
    assert dto.agendamento_id_sgg == "R1" and dto.agenda_nome == "Recepção"
    assert dto.horario.strftime("%H:%M") == "08:00"
    log = edicao.listar_logs().executar(1)[0]
    assert log.tipo == TipoOperacao.ATUALIZACAO_STATUS and log.sucesso
    assert log.agendamento_id_sgg == "R1"


def test_so_o_primeiro_agendamento_do_dia_na_recepcao_e_editado(edicao, sgg):
    marcado_na_recepcao(sgg, "R2", "P1", "A6", time(9, 0))
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0))

    checkin(edicao, MARIA)

    assert sgg.obter_agendamento("R1").status == StatusAgendamento.AGUARDANDO
    assert sgg.obter_agendamento("R2").status == StatusAgendamento.AGENDADO


def test_preferencial_fica_so_na_auditoria(edicao, sgg):
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0))
    checkin(edicao, MARIA, TipoAtendimento.PREFERENCIAL)
    assert sgg.obter_agendamento("R1").observacao is None  # a API não altera a observação
    assert edicao.listar_logs().executar(1)[0].tipo_atendimento == TipoAtendimento.PREFERENCIAL


def test_sem_agendamento_na_recepcao_cria_encaixe(edicao, sgg):
    """Maria tem agendamento no consultório (AG1), mas no modo de edição só a recepção conta."""
    dto = checkin(edicao, MARIA, TipoAtendimento.PREFERENCIAL)

    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    assert dto.agenda_nome == "Encaixe Recepção"
    assert criado.agenda_id_sgg == ENCAIXE
    assert criado.status == StatusAgendamento.AGUARDANDO
    assert criado.observacao == "[PREFERENCIAL] Encaixe via totem 08:15"


@pytest.mark.parametrize(
    "status",
    [StatusAgendamento.FALTOU, StatusAgendamento.CANCELADO, StatusAgendamento.ATENDIDO],
)
def test_agendamento_que_nao_esta_agendado_vira_encaixe(edicao, sgg, status):
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0), status)
    dto = checkin(edicao, MARIA)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    assert sgg.obter_agendamento("R1").status == status  # o totem não desfaz falta nem cancelamento


def test_encaixe_so_uma_vez_por_dia(edicao, sgg):
    primeiro = checkin(edicao, JOAO)
    with pytest.raises(CheckinJaRealizadoError):  # ainda aguardando
        checkin(edicao, JOAO)

    sgg.atualizar_status_agendamento(primeiro.agendamento_id_sgg, StatusAgendamento.ATENDIDO)
    antes = sgg.ids_agendamentos()
    with pytest.raises(AgendaEncaixeNaoConfiguradaError):  # o SGG não aceitaria outro hoje
        checkin(edicao, JOAO)
    assert sgg.ids_agendamentos() == antes
    assert (
        edicao.listar_logs().executar(1)[0].mensagem
        == "Paciente já passou pela agenda de encaixe hoje"
    )


def test_agendamento_da_recepcao_ja_aguardando_e_chegada_repetida(edicao, sgg):
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0), StatusAgendamento.AGUARDANDO)
    with pytest.raises(CheckinJaRealizadoError):
        checkin(edicao, MARIA)


def test_chegada_feita_no_modo_de_criacao_vale_depois_da_troca(container_configurado, sgg):
    checkin(container_configurado, JOAO)  # modo de criação: registro Aguardando na recepção
    container_configurado.salvar_totem().executar(ModoTotem.EDICAO, ["A4", "A6"], ENCAIXE, "admin")
    antes = sgg.ids_agendamentos()
    with pytest.raises(CheckinJaRealizadoError):
        checkin(container_configurado, JOAO)
    assert sgg.ids_agendamentos() == antes


def test_empresa_inativa_nao_edita(edicao, sgg):
    marcado_na_recepcao(sgg, "R1", "P4", "A4", time(8, 0))
    with pytest.raises(EmpresaInativaError):
        checkin(edicao, CARLOS_EMPRESA_INATIVA)
    assert sgg.obter_agendamento("R1").status == StatusAgendamento.AGENDADO


def test_identificacao_mostra_o_agendamento_da_recepcao(edicao, sgg):
    sem = edicao.identificar_paciente().executar(MARIA)
    assert sem.possui_agendamento_hoje is False  # AG1 é do consultório: não conta neste modo

    marcado_na_recepcao(sgg, "R1", "P1", "A6", time(8, 0))
    com = edicao.identificar_paciente().executar(MARIA)
    assert com.possui_agendamento_hoje is True
    assert com.agenda_nome == "Guichê 2" and com.agendamento_horario.strftime("%H:%M") == "08:00"


def test_modo_de_criacao_ignora_agendamento_marcado_na_recepcao(container_configurado, sgg):
    """Na criação, um Agendado marcado na recepção não é chegada nem o agendamento do paciente."""
    marcado_na_recepcao(sgg, "R1", "P1", "A4", time(8, 0))
    dto = checkin(container_configurado, MARIA)

    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert dto.resultado == ResultadoCheckin.AGENDAMENTO_CONFIRMADO
    assert dto.agenda_nome.startswith("Clínico Geral")  # AG1, do consultório
    assert criado.agenda_id_sgg == "A6"  # A4 já tem registro dele hoje (D16026)
    assert sgg.obter_agendamento("R1").status == StatusAgendamento.AGENDADO
