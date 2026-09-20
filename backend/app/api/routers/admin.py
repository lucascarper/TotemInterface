from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api import schemas
from app.api.deps import ContainerDep, require_admin
from app.application.dto import ConfiguracaoAgendaEntradaDTO

router = APIRouter(prefix="/admin", tags=["admin"])
protegido = APIRouter(dependencies=[Depends(require_admin)])


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, container: ContainerDep):
    if not container.auth.verify_admin_credentials(body.username, body.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuário ou senha inválidos.")
    return schemas.TokenResponse(
        access_token=container.auth.create_access_token(body.username),
        expires_in_minutes=container.settings.jwt_expires_minutes,
    )


@protegido.get("/configuracoes", response_model=list[schemas.ConfiguracaoAgendaItem])
def listar_configuracoes(container: ContainerDep):
    return [
        schemas.ConfiguracaoAgendaItem(**asdict(d))
        for d in container.listar_configuracoes().executar()
    ]


@protegido.put("/configuracoes", status_code=status.HTTP_204_NO_CONTENT)
def salvar_configuracoes(body: schemas.SalvarConfiguracoesRequest, container: ContainerDep):
    container.salvar_configuracoes().executar(
        [ConfiguracaoAgendaEntradaDTO(**c.model_dump()) for c in body.configuracoes]
    )


@protegido.post("/sincronizar", response_model=schemas.SincronizacaoResponse)
def sincronizar(container: ContainerDep):
    r = container.sincronizar().executar()
    return schemas.SincronizacaoResponse(
        agendas=r.agendas, locais=r.locais, executado_em=r.executado_em
    )


@protegido.post("/encaixe-automatico/executar", response_model=schemas.EncaixeAutomaticoResponse)
def executar_encaixe_automatico(container: ContainerDep, simular: bool = Query(True)):
    """Simula (padrão) ou executa agora a inclusão automática no encaixe.

    A simulação considera toda agenda monitorada com encaixe, mesmo sem a opção ligada,
    para o administrador ver o efeito antes de ativar. A execução real só age nas
    agendas com a opção ligada.
    """
    r = container.incluir_no_encaixe().executar(simular=simular)
    return schemas.EncaixeAutomaticoResponse(
        simulado=r.simulado,
        incluidos=[schemas.InclusaoItem(**asdict(i)) for i in r.incluidos],
        ja_existiam=r.ja_existiam,
        sem_cadastro=r.sem_cadastro,
        recusados=r.recusados,
        adiados=r.adiados,
        avisos=r.avisos,
    )


@protegido.get("/sincronizacao", response_model=schemas.StatusSincronizacao)
def status_sincronizacao(container: ContainerDep):
    with container.uow as uow:
        ultima = uow.sincronizacoes.ultima_execucao() or {}
    return schemas.StatusSincronizacao(
        executado_em=ultima.get("executado_em"),
        sucesso=ultima.get("sucesso"),
        mensagem=ultima.get("mensagem"),
        intervalo_segundos=container.settings.sync_interval_seconds,
        modo_sgg=container.settings.sgg_mode,
    )


@protegido.get("/logs", response_model=list[schemas.LogItem])
def listar_logs(container: ContainerDep, limite: int = Query(100, ge=1, le=500)):
    return [schemas.LogItem(**asdict(log)) for log in container.listar_logs().executar(limite)]


router.include_router(protegido)
