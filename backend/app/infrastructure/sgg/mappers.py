"""Tradução entre o JSON da API v3 do SGG e as entidades do domínio."""

from __future__ import annotations

import json
import re
from datetime import datetime

from app.domain.entities import (
    Agenda,
    Agendamento,
    Cpf,
    LocalAtendimento,
    Paciente,
    StatusAgendamento,
    TipoAtendimento,
)
from app.infrastructure.clock import TZ

# Valores exatos usados pelo SGG no campo `situacao` do agendamento.
_STATUS_DE_SGG = {
    "agendado": StatusAgendamento.AGENDADO,
    "aguardando": StatusAgendamento.AGUARDANDO,
    "em atendimento": StatusAgendamento.EM_ATENDIMENTO,
    "atendido": StatusAgendamento.ATENDIDO,
    "cancelado": StatusAgendamento.CANCELADO,
    "faltou": StatusAgendamento.FALTOU,
}
_STATUS_PARA_SGG = {
    StatusAgendamento.AGUARDANDO: "Aguardando",
    StatusAgendamento.EM_ATENDIMENTO: "Em Atendimento",
    StatusAgendamento.ATENDIDO: "Atendido",
    StatusAgendamento.CANCELADO: "Cancelado",
    StatusAgendamento.FALTOU: "Faltou",
}


def _texto(valor) -> str | None:
    if valor is None:
        return None
    s = str(valor).strip()
    return s or None


def unwrap_list(payload) -> list[dict]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        return [payload]
    return []


_RETURN_INFO_BRUTO = re.compile(r'"returnInfo"\s*:\s*"(\{.*\})"\s*,\s*"statusCode"', re.S)


def parse_resposta(texto: str) -> dict:
    """Decodifica a resposta do SGG, tolerando o JSON malformado das escritas.

    Nas operações POST/PUT o SGG devolve o `returnInfo` embutido sem escape, ex.:
    ``{"returnInfo":"{"erro":"D16028","msg":"..."}","statusCode":"D000",...}``
    o que não é JSON válido. Extraímos o objeto interno e reconstruímos o envelope.
    """
    try:
        data = json.loads(texto)
        return data if isinstance(data, dict) else {"resultado": data}
    except ValueError:
        pass
    m = _RETURN_INFO_BRUTO.search(texto)
    if not m:
        raise ValueError("Resposta do SGG não é JSON")
    envelope_txt = texto[: m.start()] + '"returnInfo":null,"statusCode"' + texto[m.end() :]
    envelope = json.loads(envelope_txt)
    envelope["returnInfo"] = parse_return_info(m.group(1))
    return envelope


def parse_return_info(raw) -> dict:
    """`returnInfo` chega como string JSON (às vezes já como objeto)."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except ValueError:
            return {"msg": raw}
    return {}


def status_from_sgg(valor) -> StatusAgendamento:
    return _STATUS_DE_SGG.get(str(valor or "").strip().lower(), StatusAgendamento.OUTRO)


def status_to_sgg(status: StatusAgendamento) -> str:
    return _STATUS_PARA_SGG.get(status, status.value.title())


def to_agenda(d: dict) -> Agenda:
    duracao = _texto(d.get("duracao_padrao_minutos"))
    return Agenda(
        id_sgg=str(d.get("id_agenda")),
        nome=str(d.get("nome", "")).strip(),
        local_id_sgg=_texto(d.get("id_unidade_atendimento")),
        ativa=str(d.get("situacao", "")).strip().lower() == "ativa",
        por_ordem_chegada=str(d.get("forma_atendimento", "")).strip().lower() == "chegada",
        duracao_padrao_minutos=int(duracao) if duracao and duracao.isdigit() else None,
    )


def to_local(d: dict) -> LocalAtendimento:
    return LocalAtendimento(
        id_sgg=str(d.get("id_unidade_atendimento")),
        nome=str(d.get("fantasia") or d.get("nome") or "").strip(),
        ativo=str(d.get("situacao", "ativa")).strip().lower() in ("ativa", "ativo", ""),
    )


def to_paciente(d: dict) -> Paciente:
    return Paciente(
        id_sgg=str(d.get("id_funcionario")),
        nome=str(d.get("nome", "")).strip(),
        cpf=Cpf(str(d.get("CPF") or d.get("cpf") or "")),
        data_nascimento=_texto(d.get("data_nascimento")),
        telefone=_texto(d.get("fone_celular")) or _texto(d.get("fone_comercial")),
        empresa_id_sgg=_texto(d.get("id_empresa")),
    )


def _data_hora(d: dict) -> datetime:
    data = _texto(d.get("data_agendamento"))
    hora = _texto(d.get("hora_agendamento"))
    if data and hora and hora != "99:99":
        return datetime.strptime(f"{data} {hora}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    # Ordem de chegada: sem hora marcada. Usamos a criação para ordenar.
    criacao = _texto(d.get("data_hora_criacao"))
    if criacao:
        return datetime.strptime(criacao, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
    return datetime.strptime(data or "1970-01-01", "%Y-%m-%d").replace(tzinfo=TZ)


def to_agendamento(d: dict, agenda_id_sgg: str) -> Agendamento:
    obs = _texto(d.get("observacoes"))
    tipo = None
    if obs:
        low = obs.lower()
        if "preferencial" in low:
            tipo = TipoAtendimento.PREFERENCIAL
        elif "normal" in low:
            tipo = TipoAtendimento.NORMAL
    return Agendamento(
        id_sgg=str(d.get("id_agendamento")),
        paciente_id_sgg=str(d.get("id_funcionario", "")),
        agenda_id_sgg=agenda_id_sgg,
        data_hora=_data_hora(d),
        status=status_from_sgg(d.get("situacao")),
        tipo_atendimento=tipo,
        observacao=obs,
        empresa_id_sgg=_texto(d.get("id_empresa")),
    )
