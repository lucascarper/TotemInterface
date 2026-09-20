"""Inclusão automática, na agenda de encaixe, dos agendamentos das outras agendas da unidade."""

from datetime import datetime, time

import pytest

from app.application.use_cases import IncluirNoEncaixeUseCase
from app.domain.entities import (
    Agendamento,
    ConfiguracaoAgenda,
    ResultadoCheckin,
    StatusAgendamento,
    TipoAtendimento,
    TipoOperacao,
)
from app.domain.exceptions import SggOperacaoRecusadaError
from app.infrastructure.clock import TZ
from tests.conftest import HOJE

JOAO_CPF = "11144477735"  # funcionário P2


def _ag(id_, pessoa, agenda, hora, status=StatusAgendamento.AGENDADO, empresa="E1"):
    return Agendamento(
        id_,
        pessoa,
        agenda,
        datetime.combine(HOJE, time(hora, 0), TZ),
        status,
        empresa_id_sgg=empresa,
    )


@pytest.fixture
def cenario(container, sgg):
    """A1 monitorada (encaixe A4, ordem de chegada, opção ligada). Fontes: A2 e A3 (unidade L1)."""
    container.sincronizar().executar()
    with container.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", True, "A4", True, True)])
        uow.commit()
    S = StatusAgendamento
    for ag in [
        _ag("X1", "P2", "A2", 9),  # P2 tem dois agendamentos no dia,
        _ag("X2", "P2", "A3", 10),  # em agendas diferentes: uma só inclusão
        _ag("X3", "P9", "A2", 11),
        _ag("X4", "P8", "A2", 9, S.ATENDIDO),
        _ag("X5", "P7", "A2", 9, S.CANCELADO),
        _ag("X6", "P6", "A2", 9, S.FALTOU),
        _ag("X7", "P10", "A5", 9),  # outra unidade
        _ag("X8", "P5", "A2", 9),  # já tem (cancelado) no encaixe hoje
        _ag("X9", "P5", "A4", 8, S.CANCELADO),
        _ag("Y1", "P4", "A2", 9, empresa=None),  # sem empresa: não dá para incluir
        _ag("Y2", "", "A2", 9),  # pessoa não cadastrada
    ]:
        sgg.adicionar_agendamento(ag)
    return container


def _uc(container, **kw):
    kw.setdefault("pausa_entre_escritas", 0)
    return IncluirNoEncaixeUseCase(container.sgg, container.uow, container.clock, **kw)


def _no_encaixe(sgg, pessoa):
    return [
        a
        for a in sgg._agendamentos.values()
        if a.agenda_id_sgg == "A4" and a.paciente_id_sgg == pessoa
    ]


def test_uma_inclusao_por_pessoa_mesmo_com_varios_agendamentos(cenario, sgg):
    r = _uc(cenario).executar()

    assert {i.funcionario_id_sgg for i in r.incluidos} == {"P2", "P9"}
    assert len(_no_encaixe(sgg, "P2")) == 1
    assert len(_no_encaixe(sgg, "P9")) == 1
    assert r.ja_existiam == 1  # P5
    assert r.sem_cadastro == 2  # P4 (sem empresa) e a pessoa não cadastrada
    # Só agendamentos "Agendado" de agendas não monitoradas da mesma unidade contam.
    for excluida in ("P8", "P7", "P6", "P10", "P1"):
        assert _no_encaixe(sgg, excluida) == []


def test_usa_o_agendamento_mais_cedo_como_origem(cenario):
    r = _uc(cenario).executar(simular=True)
    p2 = next(i for i in r.incluidos if i.funcionario_id_sgg == "P2")
    assert p2.agendamento_origem_id_sgg == "X1"


def test_reexecutar_nao_duplica(cenario, sgg):
    uc = _uc(cenario)
    uc.executar()
    segunda = uc.executar()

    assert segunda.incluidos == []
    assert segunda.ja_existiam == 3  # P2, P9 e P5
    assert len(_no_encaixe(sgg, "P2")) == 1


def test_inclusao_carrega_a_empresa_e_origem(cenario, sgg):
    _uc(cenario).executar()
    ag = _no_encaixe(sgg, "P9")[0]
    assert ag.empresa_id_sgg == "E1"
    assert "Encaixe automático" in ag.observacao and "Medicina do Trabalho" in ag.observacao


def test_simular_nao_escreve_e_ignora_a_opcao_desligada(cenario, sgg):
    with cenario.uow as uow:
        uow.configuracoes.salvar_todas([ConfiguracaoAgenda("A1", True, "A4", True, False)])
        uow.commit()
    antes = len(sgg._agendamentos)

    real = _uc(cenario).executar()
    assert real.incluidos == []  # opção desligada: nada acontece

    simulada = _uc(cenario).executar(simular=True)
    assert simulada.simulado and {i.funcionario_id_sgg for i in simulada.incluidos} == {"P2", "P9"}
    assert len(sgg._agendamentos) == antes


def test_limite_por_execucao_adia_o_restante(cenario, sgg):
    uc = _uc(cenario, max_por_execucao=1)
    primeira = uc.executar()
    assert len(primeira.incluidos) == 1 and primeira.adiados == 1

    segunda = uc.executar()
    assert len(segunda.incluidos) == 1
    assert {"P2", "P9"} == {p for p in ("P2", "P9") if _no_encaixe(sgg, p)}


def test_d16026_do_sgg_e_tratado_como_ja_existente(cenario, sgg, monkeypatch):
    """Se a listagem não mostrar (atraso do SGG) mas o SGG recusar com D16026, não é erro."""
    original = sgg.listar_agendamentos_da_agenda
    monkeypatch.setattr(
        sgg,
        "listar_agendamentos_da_agenda",
        lambda agenda, data: [] if agenda == "A4" else original(agenda, data),
    )
    r = _uc(cenario).executar()  # P5 já tem no encaixe: o fake recusa com D16026
    assert r.recusados == 0
    assert {i.funcionario_id_sgg for i in r.incluidos} == {"P2", "P9"}
    assert r.ja_existiam == 1


def test_recusa_do_sgg_e_registrada_e_nao_repete(cenario, sgg, monkeypatch):
    def recusar(*a, **k):
        raise SggOperacaoRecusadaError("D9999", "Agenda sem horário disponível.")

    monkeypatch.setattr(sgg, "registrar_agendamento", recusar)
    uc = _uc(cenario)
    r = uc.executar()
    assert r.recusados == 2 and r.incluidos == []

    logs = [
        x for x in cenario.listar_logs().executar() if x.tipo == TipoOperacao.ENCAIXE_AUTOMATICO
    ]
    assert len(logs) == 2 and all(not x.sucesso and "D9999" in x.mensagem for x in logs)

    # No mesmo dia não insiste (evita spam de erros na auditoria a cada ciclo).
    assert uc.executar().recusados == 0


def test_so_funciona_com_encaixe_por_ordem_de_chegada(cenario, sgg):
    next(a for a in sgg._agendas if a.id_sgg == "A4").por_ordem_chegada = False
    cenario.sincronizar().executar()
    r = _uc(cenario).executar()
    assert r.incluidos == [] and any("ordem de chegada" in a for a in r.avisos)


def test_checkin_encontra_quem_foi_incluido_no_encaixe(cenario, sgg):
    """A4 não é monitorada: sem consultá-la o totem tentaria criar outro e o SGG recusaria."""
    _uc(cenario).executar()

    dto = cenario.realizar_checkin().executar(JOAO_CPF, TipoAtendimento.NORMAL)

    assert dto.resultado == ResultadoCheckin.STATUS_ATUALIZADO
    assert _no_encaixe(sgg, "P2")[0].status == StatusAgendamento.AGUARDANDO
    assert len(_no_encaixe(sgg, "P2")) == 1
