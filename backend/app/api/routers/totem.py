from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.api import schemas
from app.api.deps import ContainerDep, require_totem

router = APIRouter(
    prefix="/totem",
    tags=["totem"],
    dependencies=[Depends(require_totem)],
    responses={
        404: {"model": schemas.ErroResponse},
        409: {"model": schemas.ErroResponse},
        422: {"model": schemas.ErroResponse},
        503: {"model": schemas.ErroResponse},
    },
)


@router.post("/identificar", response_model=schemas.IdentificarResponse)
def identificar(body: schemas.IdentificarRequest, container: ContainerDep):
    """Localiza o paciente pelo CPF e devolve dados mínimos para confirmação."""
    dto = container.identificar_paciente().executar(body.cpf)
    return schemas.IdentificarResponse(
        paciente=schemas.PacientePublico(**asdict(dto.paciente)),
        possui_agendamento_hoje=dto.possui_agendamento_hoje,
        agendamento_horario=dto.agendamento_horario,
        agenda_nome=dto.agenda_nome,
    )


@router.post("/checkin", response_model=schemas.CheckinResponse)
def checkin(body: schemas.CheckinRequest, container: ContainerDep):
    """Confirma a chegada: Agendado → Aguardando, ou cria encaixe."""
    dto = container.realizar_checkin().executar(body.cpf, body.tipo_atendimento)
    return schemas.CheckinResponse(**asdict(dto))
