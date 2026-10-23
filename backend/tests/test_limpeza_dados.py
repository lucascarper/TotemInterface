"""Limpeza do banco local: auditoria com prazo, uma linha de sincronização e cadastro enxuto."""

from datetime import UTC, datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import func, select

from app.domain.entities import LogOperacao, TipoOperacao
from app.domain.exceptions import SggIndisponivelError
from app.infrastructure.persistence.models import AgendaModel, LogOperacaoModel, SincronizacaoModel
from app.infrastructure.scheduler import HORA_LIMPEZA, segundos_ate

SP = ZoneInfo("America/Sao_Paulo")


def contar(container, modelo) -> int:
    with container.session_factory() as s:
        return s.scalar(select(func.count()).select_from(modelo))


def gravar_log(container, mensagem: str, criado_em: datetime) -> None:
    with container.uow as uow:
        log = uow.logs.registrar(LogOperacao(TipoOperacao.BUSCA_PACIENTE, True, mensagem))
        uow.commit()
    with container.session_factory() as s:
        s.get(LogOperacaoModel, log.id).criado_em = criado_em
        s.commit()


def test_apaga_auditoria_mais_antiga_que_o_prazo(container_configurado):
    # O relógio dos testes está em 17/09/2026 08:15 (São Paulo); prazo padrão de 30 dias.
    gravar_log(container_configurado, "antigo", datetime(2026, 8, 1, 12, tzinfo=UTC))
    gravar_log(container_configurado, "recente", datetime(2026, 9, 10, 12, tzinfo=UTC))

    r = container_configurado.limpar_dados().executar()

    assert r.logs_apagados == 1
    mensagens = [log.mensagem for log in container_configurado.listar_logs().executar()]
    assert "recente" in mensagens and "antigo" not in mensagens


def test_apaga_agendas_inativas_que_nao_estao_em_uso(container_configurado, sgg):
    sgg._agendas = [a for a in sgg._agendas if a.id_sgg not in ("A3", "A5")]
    container_configurado.sincronizar().executar()  # A3 e A5 ficam inativas
    with container_configurado.uow as uow:  # A5 ainda referenciada (ex.: encaixe antigo)
        totem = uow.totem.obter()
        totem.agenda_encaixe_id_sgg = "A5"
        uow.totem.salvar(totem)
        uow.commit()

    r = container_configurado.limpar_dados().executar()

    assert r.agendas_apagadas == 1
    with container_configurado.session_factory() as s:
        ids = set(s.scalars(select(AgendaModel.id_sgg)))
    assert "A3" not in ids and "A5" in ids


def test_compacta_so_quando_pedido(container_configurado):
    assert container_configurado.limpar_dados().executar(compactar=False).compactado is False
    assert container_configurado.limpar_dados().executar(compactar=True).compactado is True


def test_sincronizacao_guarda_so_a_ultima_execucao(container_configurado):
    for _ in range(3):
        container_configurado.sincronizar().executar()
    assert contar(container_configurado, SincronizacaoModel) == 1


def test_sincronizacao_com_sucesso_nao_vai_para_a_auditoria(container_configurado):
    container_configurado.sincronizar().executar()
    tipos = [log.tipo for log in container_configurado.listar_logs().executar()]
    assert TipoOperacao.SINCRONIZACAO not in tipos


def test_falha_na_sincronizacao_vai_para_a_auditoria(container_configurado, sgg, monkeypatch):
    def falhar():
        raise SggIndisponivelError("fora do ar")

    monkeypatch.setattr(sgg, "listar_agendas", falhar)
    try:
        container_configurado.sincronizar().executar()
    except SggIndisponivelError:
        pass
    log = container_configurado.listar_logs().executar(1)[0]
    assert log.tipo == TipoOperacao.SINCRONIZACAO and log.sucesso is False


def test_proxima_limpeza_as_tres_da_manha():
    def agora(h, m=0):
        return datetime.combine(datetime(2026, 9, 17).date(), time(h, m), SP)

    assert HORA_LIMPEZA == time(3, 0)
    assert segundos_ate(agora(2), HORA_LIMPEZA) == 3600
    assert segundos_ate(agora(3), HORA_LIMPEZA) == 24 * 3600  # já passou: amanhã
    assert segundos_ate(agora(23, 30), HORA_LIMPEZA) == 3.5 * 3600


def test_agendador_roda_sincronizacao_e_limpeza_juntas_sem_falhar(tmp_path, settings, caplog):
    """Na inicialização as duas rotinas disparam juntas sobre o mesmo SQLite (caso do paliativo)."""
    import asyncio

    import sqlalchemy as sa

    from app.api.container import build_container
    from app.infrastructure.sgg.fake_gateway import SggFakeGateway

    engine = sa.create_engine(
        f"sqlite:///{tmp_path / 'totem.db'}", connect_args={"check_same_thread": False}
    )
    container = build_container(settings, sgg=SggFakeGateway(), engine=engine)

    async def rodar():
        await container.scheduler.start()
        await asyncio.sleep(1)
        await container.scheduler.stop()

    with caplog.at_level("INFO"):
        asyncio.run(rodar())

    assert not [r for r in caplog.records if "falhou" in r.getMessage()]
    assert any("banco compactado" in r.getMessage() for r in caplog.records)
    assert container.listar_configuracoes().executar()  # a sincronização gravou as agendas
