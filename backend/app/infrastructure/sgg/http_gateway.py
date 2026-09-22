"""Adaptador HTTP para a API v3 do SGG (https://app.sgg.net.br/api/v3/doc/).

Particularidades do contrato (verificadas contra a API real):

* Autenticação HTTP Basic: usuário = chave de API, senha vazia.
* Consultas são GET **com corpo JSON** (`paginador`, filtros). Resposta:
  ``{"resultado": [...], "temProximaPagina": bool, "statusCode": "D000"}``.
  Retorno vazio vem como HTTP 200 com ``statusCode = "D001"`` e sem ``resultado``.
* Escritas (POST/PUT) respondem ``{"returnInfo": "<JSON em string>", "statusCode": "D000"}``;
  o JSON interno traz ``{"codigo", "msg"}`` no sucesso ou ``{"erro", "msg"}`` na recusa.
* Erros da API também chegam com HTTP 200: o que vale é o ``statusCode``.
* Agendamentos referenciam a agenda pelo **nome**; mantemos um mapa nome ⇄ id.
* Limite de 60 req/min (05h–20h) ou 120 req/min; excesso responde HTTP 429.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime, timedelta

import httpx

from app.domain.entities import (
    Agenda,
    Agendamento,
    Cpf,
    LocalAtendimento,
    Paciente,
    StatusAgendamento,
    TipoAtendimento,
)
from app.domain.exceptions import SggIndisponivelError, SggOperacaoRecusadaError
from app.infrastructure.sgg import mappers

logger = logging.getLogger(__name__)

# Só estes códigos são falha de infraestrutura/autenticação: A000/A001 (chave) e S000-S006
# (servidor). Outros começando com "A" (ex.: AG016 "agendamento não encontrado") são de negócio.
_INFRA = re.compile(r"^[AS]\d{3}$")
STATUS_OK = "D000"
STATUS_VAZIO = "D001"
TAMANHO_PAGINA = 100
MAX_PAGINAS = 50


class SggHttpGateway:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: float = 8.0,
        client: httpx.Client | None = None,
    ) -> None:
        base = base_url if base_url.endswith("/") else base_url + "/"
        self._client = client or httpx.Client(
            base_url=base,
            timeout=timeout,
            auth=httpx.BasicAuth(api_key, ""),
            headers={"Accept": "application/json"},
        )
        self._agenda_por_nome: dict[str, Agenda] = {}
        self._agenda_por_id: dict[str, Agenda] = {}

    # ------------------------------------------------------------------ infra
    def _request(self, method: str, path: str, body: dict) -> dict:
        try:
            resp = self._client.request(
                method, path, json=body, headers={"Content-Type": "application/json"}
            )
        except httpx.HTTPError as exc:
            logger.error("Falha de rede com o SGG: %s %s (%s)", method, path, exc)
            raise SggIndisponivelError(f"Falha de comunicação com o SGG: {exc}") from exc

        if resp.status_code == 429:
            raise SggIndisponivelError(
                "Limite de requisições do SGG atingido. Aguarde um instante."
            )
        if resp.status_code >= 500:
            raise SggIndisponivelError(f"SGG respondeu HTTP {resp.status_code}")
        try:
            data = mappers.parse_resposta(resp.text)
        except ValueError as exc:
            logger.error(
                "Resposta não decodificável do SGG (%s %s): %.300s", method, path, resp.text
            )
            raise SggIndisponivelError("Resposta inválida do SGG") from exc
        if not isinstance(data, dict):
            raise SggIndisponivelError("Resposta inesperada do SGG")

        status = str(data.get("statusCode", STATUS_OK))
        if _INFRA.match(status):
            # Autenticação / servidor: problema de infraestrutura, não de negócio.
            raise SggIndisponivelError(f"SGG {status}: {data.get('statusMsg', '')}")
        if resp.status_code >= 400:
            raise SggIndisponivelError(f"SGG HTTP {resp.status_code}: {data.get('statusMsg', '')}")
        return data

    def _consultar(self, path: str, filtros: dict) -> list[dict]:
        """GET paginado; devolve todos os itens de `resultado`, sem repetições.

        A paginação do SGG não é confiável: a página 0 pode trazer mais linhas que o
        `tamanho` pedido e a página seguinte repete parte delas (observado: 217 linhas
        para 159 agendamentos distintos). Por isso deduplicamos por conteúdo exato e
        paramos quando uma página não traz nada novo.
        """
        itens: list[dict] = []
        vistos: set[str] = set()
        for pagina in range(MAX_PAGINAS):
            body = {**filtros, "paginador": {"pagina": pagina, "tamanho": TAMANHO_PAGINA}}
            data = self._request("GET", path, body)
            status = str(data.get("statusCode", STATUS_OK))
            if status == STATUS_VAZIO:
                break
            if status != STATUS_OK:
                raise SggOperacaoRecusadaError(status, str(data.get("statusMsg", "")))
            if "resultado" not in data:
                # D000 sem `resultado` não é "vazio" (isso é D001): tratamos como falha
                # para o totem tentar de novo em vez de agir sobre dados incompletos.
                logger.error("SGG respondeu D000 sem 'resultado' em %s: %.300s", path, data)
                raise SggIndisponivelError("Resposta incompleta do SGG")
            novos = 0
            for item in mappers.unwrap_list(data.get("resultado")):
                chave = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if chave not in vistos:
                    vistos.add(chave)
                    itens.append(item)
                    novos += 1
            if not data.get("temProximaPagina") or novos == 0:
                break
        return itens

    def _escrever(self, method: str, path: str, body: dict) -> dict:
        data = self._request(method, path, body)
        status = str(data.get("statusCode", STATUS_OK))
        if status not in (STATUS_OK, STATUS_VAZIO):
            raise SggOperacaoRecusadaError(status, str(data.get("statusMsg", "")))
        info = mappers.parse_return_info(data.get("returnInfo"))
        if "erro" in info:
            raise SggOperacaoRecusadaError(str(info["erro"]), str(info.get("msg", "")))
        return info

    # --------------------------------------------------------- mapa de agendas
    def _carregar_agendas(self) -> list[Agenda]:
        agendas = [mappers.to_agenda(i) for i in self._consultar("agenda/", {})]
        self._agenda_por_nome = {a.nome: a for a in agendas}
        self._agenda_por_id = {a.id_sgg: a for a in agendas}
        return agendas

    def _agenda_pelo_nome(self, nome: str) -> Agenda | None:
        if nome not in self._agenda_por_nome:
            self._carregar_agendas()
        return self._agenda_por_nome.get(nome)

    def _agenda_pelo_id(self, id_sgg: str) -> Agenda:
        if id_sgg not in self._agenda_por_id:
            self._carregar_agendas()
        try:
            return self._agenda_por_id[id_sgg]
        except KeyError as exc:
            raise SggOperacaoRecusadaError("AGENDA", f"Agenda {id_sgg} não existe no SGG") from exc

    # ---------------------------------------------------------------- leitura
    def listar_agendas(self) -> list[Agenda]:
        return self._carregar_agendas()

    def listar_locais(self) -> list[LocalAtendimento]:
        return [mappers.to_local(i) for i in self._consultar("unidade_atendimento/", {})]

    def buscar_paciente_por_cpf(self, cpf: Cpf) -> Paciente | None:
        itens = self._consultar("funcionario/", {"cpf": cpf.formatado})
        if not itens:
            return None
        # Um CPF pode ter mais de um vínculo; preferimos o Ativo mais recente.
        itens.sort(
            key=lambda i: (str(i.get("situacao")) != "Ativo", str(i.get("data_hora_edicao", "")))
        )
        return mappers.to_paciente(itens[0])

    def listar_agendamentos(
        self, paciente_id_sgg: str, agenda_ids_sgg: list[str], data: date
    ) -> list[Agendamento]:
        if not agenda_ids_sgg:
            return []
        itens = self._consultar(
            "agendamento/",
            {
                "id_funcionario": paciente_id_sgg,
                "data_hora_agendamento_aPartirDe": f"{data.isoformat()} 00:00:00",
                "data_hora_agendamento_ate": f"{data.isoformat()} 23:59:59",
            },
        )
        alvo = set(agenda_ids_sgg)
        saida = []
        for item in itens:
            agenda = self._agenda_pelo_nome(str(item.get("agenda", "")))
            if agenda is None or agenda.id_sgg not in alvo:
                continue
            saida.append(mappers.to_agendamento(item, agenda.id_sgg))
        return saida

    def _obter_agendamento(self, id_sgg: str) -> Agendamento:
        itens = self._consultar("agendamento/", {"codigo": id_sgg})
        if not itens:
            raise SggOperacaoRecusadaError("D16028", "Agendamento não encontrado.")
        item = itens[0]
        agenda = self._agenda_pelo_nome(str(item.get("agenda", "")))
        return mappers.to_agendamento(item, agenda.id_sgg if agenda else "")

    # ---------------------------------------------------------------- escrita
    def atualizar_status_agendamento(
        self, agendamento_id_sgg: str, status: StatusAgendamento
    ) -> Agendamento:
        self._escrever(
            "PUT",
            "agendamento/",
            {"id_agendamento": agendamento_id_sgg, "situacao": mappers.status_to_sgg(status)},
        )
        return self._obter_agendamento(agendamento_id_sgg)

    def criar_agendamento(
        self,
        paciente: Paciente,
        agenda_id_sgg: str,
        data_hora: datetime,
        tipo_atendimento: TipoAtendimento,
        observacao: str | None = None,
    ) -> Agendamento:
        if not paciente.empresa_id_sgg:
            raise SggOperacaoRecusadaError("EMPRESA", "Funcionário sem empresa vinculada no SGG.")
        agenda = self._agenda_pelo_id(agenda_id_sgg)
        body: dict = {
            "id_empresa": paciente.empresa_id_sgg,
            "id_funcionario": paciente.id_sgg,
            "agenda": agenda.nome,
            "data_agendamento": data_hora.date().isoformat(),
            "observacoes": observacao or f"Totem ({tipo_atendimento.value.lower()})",
        }
        if not agenda.por_ordem_chegada:
            # Agenda por hora marcada exige horário alinhado à grade da agenda.
            body["hora_agendamento"] = _proximo_slot(data_hora, agenda.duracao_padrao_minutos or 5)
        info = self._escrever("POST", "agendamento/", body)
        # A doc fala em "codigo", mas a API real devolve
        # {"type": "SUCESSO", "msg": "...", "id": "134424"}. Aceitamos os dois.
        novo_id = str(info.get("codigo") or info.get("id") or "")
        if not novo_id:
            raise SggOperacaoRecusadaError(
                "POST", f"SGG não devolveu o código do agendamento (retorno: {info})"
            )
        return self._obter_agendamento(novo_id)

    def listar_agendamentos_da_agenda(self, agenda_id_sgg: str, data: date) -> list[Agendamento]:
        agenda = self._agenda_pelo_id(agenda_id_sgg)
        itens = self._consultar(
            "agendamento/",
            {
                "agenda": agenda.nome,
                "data_hora_agendamento_aPartirDe": f"{data.isoformat()} 00:00:00",
                "data_hora_agendamento_ate": f"{data.isoformat()} 23:59:59",
            },
        )
        # O filtro por nome pode ser aproximado ("Guichê 1" x "Guichê 12"): confirma o nome exato.
        return [
            mappers.to_agendamento(i, agenda.id_sgg)
            for i in itens
            if str(i.get("agenda", "")).strip() == agenda.nome
        ]


def _proximo_slot(momento: datetime, duracao_minutos: int) -> str:
    """Arredonda para cima até o próximo múltiplo da duração (ex.: 10:07 → 10:10 com 5 min)."""
    passo = max(1, duracao_minutos)
    minutos = momento.hour * 60 + momento.minute
    if momento.second or momento.microsecond or minutos % passo:
        minutos = (minutos // passo + 1) * passo
    slot = momento.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(minutes=minutos)
    return slot.strftime("%H:%M")
