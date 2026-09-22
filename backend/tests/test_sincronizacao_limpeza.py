"""Agendas excluídas/inativas no SGG não podem ficar marcadas no painel."""

import pytest

from app.application.dto import ConfiguracaoAgendaEntradaDTO as Entrada
from app.domain.exceptions import ConfiguracaoInvalidaError


def _cfg(container):
    return {c.agenda_id_sgg: c for c in container.listar_configuracoes().executar()}


def _guiches(container):
    with container.uow as uow:
        return uow.guiches.obter()


def test_agenda_excluida_no_sgg_e_desmarcada_ao_sincronizar(container_configurado, sgg):
    assert _cfg(container_configurado)["A2"].monitorada is True

    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]  # excluída no SGG
    container_configurado.sincronizar().executar()

    cfg = _cfg(container_configurado)
    assert cfg["A2"].monitorada is False and cfg["A2"].ativa is False
    assert cfg["A1"].monitorada is True  # as demais seguem intactas


def test_guiche_apontando_para_agenda_excluida_e_limpo(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A4"]  # guichê 1 excluído
    container_configurado.sincronizar().executar()

    guiches = _guiches(container_configurado)
    assert guiches.guiche_1_agenda_id_sgg is None
    assert guiches.guiche_2_agenda_id_sgg == "A6"  # o outro guichê segue intacto


def test_agenda_inativa_no_sgg_deixa_de_ser_monitorada(container_configurado, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A1").ativa = False
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado)["A1"].monitorada is False


def test_guiche_inativo_no_sgg_e_limpo(container_configurado, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A6").ativa = False
    container_configurado.sincronizar().executar()
    guiches = _guiches(container_configurado)
    assert guiches.guiche_1_agenda_id_sgg == "A4"
    assert guiches.guiche_2_agenda_id_sgg is None


def test_sincronizar_sem_mudancas_preserva_configuracao(container_configurado):
    antes = _cfg(container_configurado)
    antes_guiches = _guiches(container_configurado)
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado) == antes
    assert _guiches(container_configurado) == antes_guiches


def test_salvar_normaliza_agenda_inativa(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]
    container_configurado.sincronizar().executar()
    salvar = container_configurado.salvar_configuracoes()

    # O painel ainda pode mandar A2 marcada: o backend salva como desmarcada.
    salvar.executar([Entrada("A1", True), Entrada("A2", True)])
    assert _cfg(container_configurado)["A2"].monitorada is False

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar([Entrada("A1", True), Entrada("A1", True)])  # agenda repetida


def test_salvar_guiches_rejeita_agenda_desconhecida_inativa_ou_por_hora(container_configurado, sgg):
    salvar = container_configurado.salvar_guiches()

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar("A999", None)  # desconhecida

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar("A1", None)  # A1 é por hora marcada, não ordem de chegada

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar("A4", "A4")  # os dois guichês não podem ser a mesma agenda

    next(a for a in sgg._agendas if a.id_sgg == "A6").ativa = False
    container_configurado.sincronizar().executar()
    with pytest.raises(ConfiguracaoInvalidaError):
        container_configurado.salvar_guiches().executar("A4", "A6")  # A6 está inativa


def test_salvar_guiches_aceita_configuracao_valida(container_configurado):
    container_configurado.salvar_guiches().executar("A4", "A6")
    guiches = _guiches(container_configurado)
    assert guiches.guiche_1_agenda_id_sgg == "A4"
    assert guiches.guiche_2_agenda_id_sgg == "A6"
