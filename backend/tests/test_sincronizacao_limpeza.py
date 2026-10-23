"""Agendas excluídas/inativas no SGG não podem ficar marcadas no painel."""

import pytest

from app.application.dto import ConfiguracaoAgendaEntradaDTO as Entrada
from app.domain.entities import ModoTotem, TipoOperacao
from app.domain.exceptions import ConfiguracaoInvalidaError


def _cfg(container):
    return {c.agenda_id_sgg: c for c in container.listar_configuracoes().executar()}


def _totem(container):
    with container.uow as uow:
        return uow.totem.obter()


def test_agenda_excluida_no_sgg_e_desmarcada_ao_sincronizar(container_configurado, sgg):
    assert _cfg(container_configurado)["A2"].monitorada is True

    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]  # excluída no SGG
    container_configurado.sincronizar().executar()

    cfg = _cfg(container_configurado)
    assert cfg["A2"].monitorada is False and cfg["A2"].ativa is False
    assert cfg["A1"].monitorada is True  # as demais seguem intactas


def test_recepcao_apontando_para_agenda_excluida_e_limpa(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A4"]  # 1ª da recepção excluída
    container_configurado.sincronizar().executar()
    assert _totem(container_configurado).agendas_recepcao == ["A6"]  # a outra segue intacta


def test_agenda_inativa_no_sgg_deixa_de_ser_monitorada(container_configurado, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A1").ativa = False
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado)["A1"].monitorada is False


def test_recepcao_e_encaixe_inativos_no_sgg_sao_limpos(container_configurado, sgg):
    container_configurado.salvar_totem().executar(ModoTotem.EDICAO, ["A4", "A6"], "A7", "admin")
    for a in sgg._agendas:
        if a.id_sgg in ("A6", "A7"):
            a.ativa = False
    container_configurado.sincronizar().executar()
    totem = _totem(container_configurado)
    assert totem.agendas_recepcao == ["A4"]
    assert totem.agenda_encaixe_id_sgg is None


def test_sincronizar_sem_mudancas_preserva_configuracao(container_configurado):
    antes = _cfg(container_configurado)
    antes_totem = _totem(container_configurado)
    container_configurado.sincronizar().executar()
    assert _cfg(container_configurado) == antes
    assert _totem(container_configurado) == antes_totem


def test_salvar_normaliza_agenda_inativa(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg != "A2"]
    container_configurado.sincronizar().executar()
    salvar = container_configurado.salvar_configuracoes()

    # O painel ainda pode mandar A2 marcada: o backend salva como desmarcada.
    salvar.executar([Entrada("A1", True), Entrada("A2", True)])
    assert _cfg(container_configurado)["A2"].monitorada is False

    with pytest.raises(ConfiguracaoInvalidaError):
        salvar.executar([Entrada("A1", True), Entrada("A1", True)])  # agenda repetida


@pytest.mark.parametrize(
    ("modo", "recepcao", "encaixe", "trecho"),
    [
        (ModoTotem.CRIACAO, ["A999"], None, "desconhecida"),
        (ModoTotem.CRIACAO, ["A4", "A4"], None, "duas vezes"),
        (ModoTotem.CRIACAO, ["A4"], "A1", "ordem de chegada"),  # A1 é por hora marcada
        (ModoTotem.CRIACAO, ["A4", "A7"], "A7", "não pode ser"),
        (ModoTotem.EDICAO, [], "A7", "ao menos uma"),
        (ModoTotem.EDICAO, ["A4"], None, "encaixe"),
    ],
)
def test_salvar_totem_rejeita_configuracao_invalida(
    container_configurado, modo, recepcao, encaixe, trecho
):
    with pytest.raises(ConfiguracaoInvalidaError, match=trecho):
        container_configurado.salvar_totem().executar(modo, recepcao, encaixe, "admin")


def test_salvar_totem_rejeita_agenda_inativa(container_configurado, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A6").ativa = False
    container_configurado.sincronizar().executar()
    with pytest.raises(ConfiguracaoInvalidaError, match="inativa"):
        container_configurado.salvar_totem().executar(
            ModoTotem.CRIACAO, ["A4", "A6"], None, "admin"
        )


def test_salvar_totem_aceita_hora_marcada_na_recepcao(container_configurado):
    container_configurado.salvar_totem().executar(ModoTotem.CRIACAO, ["A4", "A1"], None, "admin")
    assert _totem(container_configurado).agendas_recepcao == ["A4", "A1"]


def test_salvar_totem_so_audita_troca_de_modo(container_configurado):
    salvar = container_configurado.salvar_totem()
    salvar.executar(ModoTotem.CRIACAO, ["A4"], None, "admin")  # mesmo modo: não audita
    salvar.executar(ModoTotem.EDICAO, ["A4"], "A7", "maria")
    logs = [
        log
        for log in container_configurado.listar_logs().executar()
        if log.tipo == TipoOperacao.CONFIGURACAO
    ]
    assert len(logs) == 1 and "edição" in logs[0].mensagem and "maria" in logs[0].mensagem


def test_salvar_totem_descarta_ultima_usada_que_saiu_da_lista(container_configurado):
    with container_configurado.uow as uow:
        cfg = uow.totem.obter()
        cfg.ultima_recepcao_usada = "A6"
        uow.totem.salvar(cfg)
        uow.commit()
    container_configurado.salvar_totem().executar(ModoTotem.CRIACAO, ["A4"], None, "admin")
    assert _totem(container_configurado).ultima_recepcao_usada is None
