"""Agendas excluídas/inativas no SGG não podem ficar marcadas no painel."""

import pytest

from app.application.dto import ConfiguracaoAgendaEntradaDTO as Entrada
from app.domain.exceptions import ConfiguracaoInvalidaError


def _cfg(container):
    return {c.agenda_id_sgg: c for c in container.listar_configuracoes().executar()}


def test_agenda_excluida_no_sgg_e_desmarcada_ao_sincronizar(container_configurado, sgg):
    assert _cfg(container_configurado)["A2"].monitorada is True

    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]  # excluída no SGG
    container_configurado.sincronizar().executar()

    cfg = _cfg(container_configurado)
    assert cfg["A2"].monitorada is False and cfg["A2"].ativa is False
    assert cfg["A2"].agenda_encaixe_id_sgg is None
    assert cfg["A1"].monitorada is True  # as demais seguem intactas
    assert cfg["A1"].agenda_encaixe_id_sgg == "A4"


def test_encaixe_apontando_para_agenda_excluida_e_limpo(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A4"]
    container_configurado.sincronizar().executar()

    cfg = _cfg(container_configurado)
    assert cfg["A1"].monitorada is True
    assert cfg["A1"].agenda_encaixe_id_sgg is None
    assert cfg["A1"].encaixe_padrao is False


def test_agenda_inativa_no_sgg_deixa_de_ser_monitorada(container_configurado, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A1").ativa = False
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado)["A1"].monitorada is False


def test_sincronizar_sem_mudancas_preserva_configuracao(container_configurado):
    antes = _cfg(container_configurado)
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado) == antes


def test_salvar_normaliza_agenda_inativa_e_rejeita_encaixe_inativo(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]
    container_configurado.sincronizar().executar()
    salvar = container_configurado.salvar_configuracoes()

    # O painel ainda pode mandar A2 marcada: o backend salva como desmarcada.
    salvar.executar([Entrada("A1", True, "A4", True), Entrada("A2", True, "A4", False)])
    assert _cfg(container_configurado)["A2"].monitorada is False

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar([Entrada("A1", True, "A2", False)])  # encaixe em agenda excluída
