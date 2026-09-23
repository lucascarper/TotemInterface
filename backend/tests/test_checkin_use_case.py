from datetime import date, datetime, time

import pytest

from app.domain.entities import (
    Agendamento,
    ConfiguracaoAgenda,
    ConfiguracaoGuiches,
    ResultadoCheckin,
    StatusAgendamento,
    TipoAtendimento,
    TipoOperacao,
)
from app.domain.exceptions import (
    AgendaEncaixeNaoConfiguradaError,
    CheckinJaRealizadoError,
    PacienteNaoEncontradoError,
    SggOperacaoRecusadaError,
)
from app.infrastructure.clock import TZ

MARIA, JOAO, ANA = "52998224725", "11144477735", "12345678909"
HOJE = date(2026, 9, 17)


# ------------------------------------------------------------- fluxo completo
def test_checkin_confirma_agendamento_criando_registro_no_guiche(container_configurado, sgg):
    """O agendamento original nunca é tocado: um novo registro nasce num guichê."""
    dto = container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)

    assert dto.resultado == ResultadoCheckin.AGENDAMENTO_CONFIRMADO
    assert dto.agenda_nome.startswith("Clínico Geral")  # mostra a agenda original ao paciente
    assert dto.horario.strftime("%H:%M") == "09:30"  # horário do agendamento original

    original = sgg.obter_agendamento("AG1")
    assert original.status == StatusAgendamento.AGENDADO  # nunca alterado

    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert criado.id_sgg != "AG1"
    assert criado.agenda_id_sgg == "A4"  # empate inicial (nenhum histórico): vai para o guichê 1
    assert criado.status == StatusAgendamento.AGUARDANDO
    assert "Clínico Geral" in criado.observacao
    assert not criado.observacao.startswith("[PREFERENCIAL]")  # Normal não leva marcador
    # Horário da chegada (agora, via FixedClock) distinto do horário do agendamento original.
    assert criado.observacao == (
        "Chegada via totem 08:15 - agendado 09:30 em Clínico Geral - Dr. Roberto"
    )


def test_checkin_preferencial_marca_observacao_com_prefixo(container_configurado, sgg):
    """O marcador vem no início (não no fim), pois listas do SGG podem truncar o texto."""
    dto = container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.PREFERENCIAL)
    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert criado.observacao.startswith("[PREFERENCIAL] ")


def test_checkin_cria_encaixe_quando_nao_ha_agendamento(container_configurado, sgg):
    dto = container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.PREFERENCIAL)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    criado = sgg.obter_agendamento(dto.agendamento_id_sgg)
    assert criado.agenda_id_sgg == "A4"
    assert criado.status == StatusAgendamento.AGUARDANDO
    assert criado.tipo_atendimento == TipoAtendimento.PREFERENCIAL
    assert dto.agenda_nome == "Recepção"
    assert criado.observacao == "[PREFERENCIAL] Encaixe via totem 08:15"


def test_checkin_repetido_nao_duplica(container_configurado):
    """Fixture: Ana já tem um registro Aguardando hoje (simula chegada já processada)."""
    with pytest.raises(CheckinJaRealizadoError):
        container_configurado.realizar_checkin().executar(ANA, TipoAtendimento.NORMAL)


def test_checkin_repetido_via_guiche_nao_duplica(container_configurado):
    dto1 = container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)
    assert dto1.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    with pytest.raises(CheckinJaRealizadoError):
        container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)


def test_paciente_nao_cadastrado(container_configurado):
    with pytest.raises(PacienteNaoEncontradoError):
        container_configurado.realizar_checkin().executar("390.533.447-05", TipoAtendimento.NORMAL)


def test_sem_guiche_configurado_sem_agendamento(container):
    container.sincronizar().executar()
    with container.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", True)])
        uow.commit()
    with pytest.raises(AgendaEncaixeNaoConfiguradaError):
        container.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)


def test_sem_guiche_configurado_mesmo_com_agendamento(container):
    """Ter um agendamento hoje não dispensa o guichê: ele é sempre necessário agora."""
    container.sincronizar().executar()
    with container.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", True)])
        uow.commit()
    with pytest.raises(AgendaEncaixeNaoConfiguradaError):
        container.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)


def test_agenda_nao_monitorada_e_ignorada(container_configurado, sgg):
    """Agendamento em agenda não monitorada não conta: paciente vai para o guichê como encaixe."""
    with container_configurado.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", False)])
        uow.commit()
    dto = container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    assert dto.resultado == ResultadoCheckin.ENCAIXE_CRIADO
    assert sgg.obter_agendamento("AG1").status == StatusAgendamento.AGENDADO


def test_operacoes_sao_auditadas(container_configurado):
    container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    logs = container_configurado.listar_logs().executar()
    tipos = [log.tipo for log in logs]
    assert TipoOperacao.CRIACAO_AGENDAMENTO in tipos
    assert all(log.cpf_mascarado != MARIA for log in logs if log.cpf_mascarado)
    assert logs[0].cpf_mascarado == "***.982.247-**"


def test_identificar_paciente_informa_agendamento(container_configurado):
    dto = container_configurado.identificar_paciente().executar(MARIA)
    assert dto.possui_agendamento_hoje is True
    assert dto.paciente.nome == "Maria Silva"
    assert dto.paciente.cpf_mascarado == "***.982.247-**"
    assert dto.paciente.telefone_mascarado == "(**) *****-4321"


def test_recusa_do_sgg_e_auditada(container_configurado, sgg):
    def recusar(*a, **k):
        raise SggOperacaoRecusadaError("D16026", "Já possui compromisso nesta agenda hoje.")

    sgg.criar_agendamento = recusar
    with pytest.raises(SggOperacaoRecusadaError):
        container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)
    ultimo = container_configurado.listar_logs().executar(1)[0]
    assert ultimo.tipo == TipoOperacao.ERRO and "D16026" in ultimo.mensagem


def test_recusa_do_sgg_ao_confirmar_agendamento_e_auditada(container_configurado, sgg):
    """A mesma proteção vale para quem tinha agendamento (caminho agora unificado)."""

    def recusar(*a, **k):
        raise SggOperacaoRecusadaError("D16026", "Já possui compromisso nesta agenda hoje.")

    sgg.criar_agendamento = recusar
    with pytest.raises(SggOperacaoRecusadaError):
        container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.NORMAL)
    assert sgg.obter_agendamento("AG1").status == StatusAgendamento.AGENDADO


# ---------------------------------------------------- distribuição entre guichês
def _aguardando(agenda_id: str, n: int, prefixo: str) -> list[Agendamento]:
    return [
        Agendamento(
            f"{prefixo}{i}",
            f"PX{i}",
            agenda_id,
            datetime.combine(HOJE, time(9, i), TZ),
            StatusAgendamento.AGUARDANDO,
        )
        for i in range(n)
    ]


def test_checkin_preferencial_sempre_no_guiche_1_mesmo_mais_carregado(container_configurado, sgg):
    """Preferencial não participa do balanceamento: vai sempre para o guichê 1."""
    for ag in _aguardando("A4", 5, "F"):
        sgg.adicionar_agendamento(ag)
    dto = container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.PREFERENCIAL)
    assert sgg.obter_agendamento(dto.agendamento_id_sgg).agenda_id_sgg == "A4"


def test_checkin_normal_vai_para_guiche_menos_carregado(container_configurado, sgg):
    for ag in _aguardando("A4", 3, "F"):
        sgg.adicionar_agendamento(ag)
    dto = container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)
    assert sgg.obter_agendamento(dto.agendamento_id_sgg).agenda_id_sgg == "A6"


def test_checkin_normal_persiste_ultimo_guiche_para_desempate(container_configurado):
    container_configurado.realizar_checkin().executar(JOAO, TipoAtendimento.NORMAL)
    with container_configurado.uow as uow:
        assert uow.guiches.obter().ultimo_guiche_usado == 1  # empate inicial resolve para o 1


def test_checkin_preferencial_nao_altera_o_desempate(container_configurado):
    with container_configurado.uow as uow:
        cfg = uow.guiches.obter()
        cfg.ultimo_guiche_usado = 2
        uow.guiches.salvar(cfg)
        uow.commit()
    container_configurado.realizar_checkin().executar(MARIA, TipoAtendimento.PREFERENCIAL)
    with container_configurado.uow as uow:
        assert uow.guiches.obter().ultimo_guiche_usado == 2  # não mudou


def test_resolver_guiche_empate_alterna_por_ultimo_usado(container_configurado):
    uc = container_configurado.realizar_checkin()
    sem_historico = ConfiguracaoGuiches("A4", "A6")
    assert uc._resolver_guiche(sem_historico, TipoAtendimento.NORMAL, HOJE) == ("A4", 1)

    usou_1 = ConfiguracaoGuiches("A4", "A6", ultimo_guiche_usado=1)
    assert uc._resolver_guiche(usou_1, TipoAtendimento.NORMAL, HOJE) == ("A6", 2)

    usou_2 = ConfiguracaoGuiches("A4", "A6", ultimo_guiche_usado=2)
    assert uc._resolver_guiche(usou_2, TipoAtendimento.NORMAL, HOJE) == ("A4", 1)


def test_resolver_guiche_com_um_unico_configurado(container_configurado):
    uc = container_configurado.realizar_checkin()
    so_guiche_1 = ConfiguracaoGuiches("A4", None)
    assert uc._resolver_guiche(so_guiche_1, TipoAtendimento.PREFERENCIAL, HOJE) == ("A4", 1)
    assert uc._resolver_guiche(so_guiche_1, TipoAtendimento.NORMAL, HOJE) == ("A4", 1)

    so_guiche_2 = ConfiguracaoGuiches(None, "A6")
    assert uc._resolver_guiche(so_guiche_2, TipoAtendimento.NORMAL, HOJE) == ("A6", 2)


def test_resolver_guiche_nenhum_configurado(container_configurado):
    uc = container_configurado.realizar_checkin()
    assert uc._resolver_guiche(ConfiguracaoGuiches(), TipoAtendimento.NORMAL, HOJE) == (None, None)
