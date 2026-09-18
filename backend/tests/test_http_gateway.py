"""Testa o adaptador HTTP contra o contrato real do SGG usando transporte falso."""

import json
from datetime import datetime

import httpx
import pytest

from app.domain.entities import Cpf, StatusAgendamento, TipoAtendimento
from app.domain.exceptions import SggIndisponivelError, SggOperacaoRecusadaError
from app.infrastructure.sgg.http_gateway import SggHttpGateway, _proximo_slot
from app.infrastructure.sgg.mappers import to_paciente

AGENDAS = [
    {
        "id_agenda": "65",
        "nome": "TESTE TI",
        "id_unidade_atendimento": "8",
        "situacao": "Ativa",
        "forma_atendimento": "Chegada",
        "duracao_padrao_minutos": "10",
    },
    {
        "id_agenda": "63",
        "nome": "Consultorio 1",
        "id_unidade_atendimento": "1",
        "situacao": "Ativa",
        "forma_atendimento": "Hora",
        "duracao_padrao_minutos": "5",
    },
    {
        "id_agenda": "60",
        "nome": "Lab",
        "id_unidade_atendimento": "",
        "situacao": "Inativa",
        "forma_atendimento": "Chegada",
        "duracao_padrao_minutos": "15",
    },
]


def ok(resultado, proxima=False):
    return {
        "resultado": resultado,
        "temProximaPagina": proxima,
        "statusCode": "D000",
        "statusMsg": "Nenhum problema ocorrido no tratamento da API.",
    }


VAZIO = {
    "statusCode": "D001",
    "statusMsg": "Nenhum problema ocorrido. Porém o retorno é em branco.",
}


def gateway(handler):
    client = httpx.Client(
        base_url="https://sgg.test/api/v3/", transport=httpx.MockTransport(handler)
    )
    return SggHttpGateway(base_url="https://sgg.test/api/v3/", api_key="k", client=client)


def body_of(req: httpx.Request) -> dict:
    return json.loads(req.content)


def test_autenticacao_basic_com_senha_vazia():
    import base64

    visto = {}

    def handler(req):
        visto["auth"] = req.headers.get("Authorization")
        visto["path"] = req.url.path
        return httpx.Response(200, json=VAZIO)

    client = httpx.Client(
        base_url="https://sgg.test/api/v3/", transport=httpx.MockTransport(handler)
    )
    g = SggHttpGateway(base_url="https://sgg.test/api/v3", api_key="CHAVE", client=client)
    g._client.auth = httpx.BasicAuth("CHAVE", "")
    g.listar_locais()
    assert visto["path"] == "/api/v3/unidade_atendimento/"
    assert visto["auth"] == "Basic " + base64.b64encode(b"CHAVE:").decode()


def test_listar_agendas_mapeia_e_pagina():
    chamadas = []

    def handler(req):
        chamadas.append(body_of(req)["paginador"]["pagina"])
        assert req.method == "GET" and req.url.path.endswith("/agenda/")
        return httpx.Response(
            200, json=ok(AGENDAS[:2], proxima=True) if chamadas[-1] == 0 else ok(AGENDAS[2:])
        )

    agendas = gateway(handler).listar_agendas()
    assert chamadas == [0, 1]
    assert [a.id_sgg for a in agendas] == ["65", "63", "60"]
    assert agendas[0].por_ordem_chegada is True and agendas[0].duracao_padrao_minutos == 10
    assert agendas[1].por_ordem_chegada is False
    assert agendas[2].ativa is False and agendas[2].local_id_sgg is None


def test_paciente_por_cpf_envia_mascara_e_retorno_vazio_vira_none():
    def handler(req):
        assert body_of(req)["cpf"] == "529.982.247-25"
        return httpx.Response(200, json=VAZIO)

    assert gateway(handler).buscar_paciente_por_cpf(Cpf("52998224725")) is None


def test_paciente_por_cpf_prefere_vinculo_ativo():
    def handler(req):
        return httpx.Response(
            200,
            json=ok(
                [
                    {
                        "id_funcionario": "1",
                        "id_empresa": "10",
                        "nome": "Maria",
                        "CPF": "529.982.247-25",
                        "situacao": "Demitido",
                        "fone_celular": "",
                        "data_nascimento": "1985-03-12",
                    },
                    {
                        "id_funcionario": "2",
                        "id_empresa": "20",
                        "nome": "Maria",
                        "CPF": "529.982.247-25",
                        "situacao": "Ativo",
                        "fone_celular": "(61) 99999-1234",
                        "data_nascimento": "1985-03-12",
                    },
                ]
            ),
        )

    p = gateway(handler).buscar_paciente_por_cpf(Cpf("52998224725"))
    assert p is not None and p.id_sgg == "2" and p.empresa_id_sgg == "20"
    assert p.telefone_mascarado == "(**) *****-1234"


def test_listar_agendamentos_filtra_por_agenda_monitorada():
    def handler(req):
        if req.url.path.endswith("/agenda/"):
            return httpx.Response(200, json=ok(AGENDAS))
        b = body_of(req)
        assert b["id_funcionario"] == "47651"
        assert b["data_hora_agendamento_aPartirDe"] == "2026-09-17 00:00:00"
        return httpx.Response(
            200,
            json=ok(
                [
                    {
                        "id_agendamento": "1",
                        "id_funcionario": "47651",
                        "agenda": "TESTE TI",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "",
                        "situacao": "Agendado",
                        "data_hora_criacao": "2026-09-17 08:00:00",
                        "observacoes": "Totem (preferencial)",
                    },
                    {
                        "id_agendamento": "2",
                        "id_funcionario": "47651",
                        "agenda": "Consultorio 1",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "10:30",
                        "situacao": "Em Atendimento",
                    },
                    {
                        "id_agendamento": "3",
                        "id_funcionario": "47651",
                        "agenda": "Lab",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "09:00",
                        "situacao": "Faltou",
                    },
                ]
            ),
        )

    from datetime import date

    itens = gateway(handler).listar_agendamentos("47651", ["65", "63"], date(2026, 9, 17))
    assert [a.id_sgg for a in itens] == ["1", "2"]
    assert itens[0].status == StatusAgendamento.AGENDADO
    assert itens[0].tipo_atendimento == TipoAtendimento.PREFERENCIAL
    assert itens[0].data_hora.hour == 8  # ordem de chegada: usa data_hora_criacao
    assert (
        itens[1].status == StatusAgendamento.EM_ATENDIMENTO
        and itens[1].data_hora.strftime("%H:%M") == "10:30"
    )


def test_atualizar_status_envia_put_e_reconsulta():
    passos = []

    def handler(req):
        if req.method == "PUT":
            b = body_of(req)
            passos.append(("PUT", b))
            assert b == {"id_agendamento": "134205", "situacao": "Aguardando"}
            return httpx.Response(
                200,
                json={
                    "returnInfo": json.dumps({"codigo": 134205, "msg": "ok"}),
                    "statusCode": "D000",
                    "statusMsg": "",
                },
            )
        if req.url.path.endswith("/agenda/"):
            return httpx.Response(200, json=ok(AGENDAS))
        b = body_of(req)
        passos.append(("GET", b))
        assert b["codigo"] == "134205"
        return httpx.Response(
            200,
            json=ok(
                [
                    {
                        "id_agendamento": "134205",
                        "id_funcionario": "1",
                        "agenda": "TESTE TI",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "",
                        "situacao": "Aguardando",
                        "data_hora_criacao": "2026-09-17 08:00:00",
                    }
                ]
            ),
        )

    ag = gateway(handler).atualizar_status_agendamento("134205", StatusAgendamento.AGUARDANDO)
    assert ag.status == StatusAgendamento.AGUARDANDO and ag.agenda_id_sgg == "65"
    assert [p[0] for p in passos] == ["PUT", "GET"]


def test_put_recusado_vira_excecao_de_negocio():
    def handler(req):
        # Formato real observado: returnInfo é uma STRING contendo JSON.
        return httpx.Response(
            200,
            json={
                "returnInfo": '{"erro":"D16028","msg":"Agendamento não encontrado."}',
                "statusCode": "D000",
                "statusMsg": "Nenhum problema ocorrido",
            },
        )

    with pytest.raises(SggOperacaoRecusadaError) as exc:
        gateway(handler).atualizar_status_agendamento("999", StatusAgendamento.AGUARDANDO)
    assert exc.value.codigo_sgg == "D16028"


def test_criar_agendamento_ordem_de_chegada_sem_hora():
    enviado = {}

    def handler(req):
        if req.url.path.endswith("/agenda/"):
            return httpx.Response(200, json=ok(AGENDAS))
        if req.method == "POST":
            enviado.update(body_of(req))
            return httpx.Response(
                200,
                json={
                    "returnInfo": json.dumps({"codigo": 777, "msg": "Cadastro efetuado"}),
                    "statusCode": "D000",
                    "statusMsg": "",
                },
            )
        return httpx.Response(
            200,
            json=ok(
                [
                    {
                        "id_agendamento": "777",
                        "id_funcionario": "47651",
                        "agenda": "TESTE TI",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "",
                        "situacao": "Agendado",
                        "data_hora_criacao": "2026-09-17 10:07:00",
                    }
                ]
            ),
        )

    paciente = to_paciente(
        {"id_funcionario": "47651", "id_empresa": "909", "nome": "L", "CPF": "529.982.247-25"}
    )
    ag = gateway(handler).criar_agendamento(
        paciente,
        "65",
        datetime(2026, 9, 17, 10, 7),
        TipoAtendimento.PREFERENCIAL,
        "Encaixe via totem (preferencial)",
    )
    assert ag.id_sgg == "777"
    assert enviado["id_empresa"] == "909" and enviado["id_funcionario"] == "47651"
    assert enviado["agenda"] == "TESTE TI" and enviado["data_agendamento"] == "2026-09-17"
    assert "hora_agendamento" not in enviado
    assert enviado["observacoes"] == "Encaixe via totem (preferencial)"


def test_criar_agendamento_hora_marcada_alinha_slot():
    enviado = {}

    def handler(req):
        if req.url.path.endswith("/agenda/"):
            return httpx.Response(200, json=ok(AGENDAS))
        if req.method == "POST":
            enviado.update(body_of(req))
            return httpx.Response(
                200, json={"returnInfo": json.dumps({"codigo": 1, "msg": ""}), "statusCode": "D000"}
            )
        return httpx.Response(
            200,
            json=ok(
                [
                    {
                        "id_agendamento": "1",
                        "id_funcionario": "1",
                        "agenda": "Consultorio 1",
                        "data_agendamento": "2026-09-17",
                        "hora_agendamento": "10:10",
                        "situacao": "Agendado",
                    }
                ]
            ),
        )

    paciente = to_paciente(
        {"id_funcionario": "1", "id_empresa": "9", "nome": "L", "CPF": "529.982.247-25"}
    )
    gateway(handler).criar_agendamento(
        paciente, "63", datetime(2026, 9, 17, 10, 7, 30), TipoAtendimento.NORMAL
    )
    assert enviado["hora_agendamento"] == "10:10"


def test_proximo_slot():
    assert _proximo_slot(datetime(2026, 1, 1, 10, 0), 5) == "10:00"
    assert _proximo_slot(datetime(2026, 1, 1, 10, 0, 1), 5) == "10:05"
    assert _proximo_slot(datetime(2026, 1, 1, 10, 7), 15) == "10:15"


def test_429_e_erro_de_autenticacao_viram_indisponivel():
    with pytest.raises(SggIndisponivelError):
        gateway(lambda req: httpx.Response(429)).listar_agendas()
    with pytest.raises(SggIndisponivelError):
        gateway(
            lambda req: httpx.Response(
                200, json={"statusCode": "A001", "statusMsg": "Chave não encontrada"}
            )
        ).listar_agendas()
    with pytest.raises(SggIndisponivelError):
        gateway(lambda req: (_ for _ in ()).throw(httpx.ConnectError("boom"))).listar_agendas()


def test_parse_resposta_tolera_json_malformado_de_escrita():
    from app.infrastructure.sgg.mappers import parse_resposta

    bruto = (
        '{"returnInfo":"{"codigo":134321,"msg":"Cadastro do Agendamento efetuado com sucesso"}",'
        '"statusCode":"D000","statusMsg":"Nenhum problema ocorrido no tratamento da API."}'
    )
    d = parse_resposta(bruto)
    assert d["statusCode"] == "D000"
    assert d["returnInfo"] == {
        "codigo": 134321,
        "msg": "Cadastro do Agendamento efetuado com sucesso",
    }
    # JSON válido continua funcionando
    assert parse_resposta('{"statusCode":"D001","statusMsg":"vazio"}')["statusCode"] == "D001"
    with pytest.raises(ValueError):
        parse_resposta("<html>erro</html>")


def test_consulta_d000_sem_resultado_vira_indisponivel():
    handler = lambda req: httpx.Response(200, json={"statusCode": "D000", "statusMsg": "ok"})  # noqa: E731
    with pytest.raises(SggIndisponivelError):
        gateway(handler).listar_locais()
