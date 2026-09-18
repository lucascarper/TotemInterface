def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_totem_identificar_e_checkin(client):
    r = client.post("/totem/identificar", json={"cpf": "529.982.247-25"})
    assert r.status_code == 200, r.text
    assert r.json()["possui_agendamento_hoje"] is True

    r = client.post("/totem/checkin", json={"cpf": "529.982.247-25", "tipo_atendimento": "NORMAL"})
    assert r.status_code == 200, r.text
    assert r.json()["resultado"] == "STATUS_ATUALIZADO"

    r = client.post("/totem/checkin", json={"cpf": "529.982.247-25", "tipo_atendimento": "NORMAL"})
    assert r.status_code == 409
    assert r.json()["codigo"] == "CHECKIN_JA_REALIZADO"


def test_totem_paciente_nao_encontrado(client):
    r = client.post("/totem/identificar", json={"cpf": "390.533.447-05"})
    assert r.status_code == 404
    assert r.json()["codigo"] == "PACIENTE_NAO_ENCONTRADO"


def test_totem_cpf_invalido(client):
    r = client.post("/totem/identificar", json={"cpf": "111.111.111-11"})
    assert r.status_code == 422
    assert r.json()["codigo"] == "CPF_INVALIDO"


def test_admin_requer_login(client):
    assert client.get("/admin/configuracoes").status_code == 401
    r = client.post("/admin/login", json={"username": "admin", "password": "errada"})
    assert r.status_code == 401


def test_admin_configuracoes_roundtrip(client, admin_headers):
    r = client.get("/admin/configuracoes", headers=admin_headers)
    assert r.status_code == 200
    itens = r.json()
    assert len(itens) == 5
    a1 = next(i for i in itens if i["agenda_id_sgg"] == "A1")
    assert a1["monitorada"] is True and a1["agenda_encaixe_id_sgg"] == "A4"

    novo = [
        {
            "agenda_id_sgg": i["agenda_id_sgg"],
            "monitorada": i["agenda_id_sgg"] == "A5",
            "agenda_encaixe_id_sgg": "A4" if i["agenda_id_sgg"] == "A5" else None,
            "encaixe_padrao": i["agenda_id_sgg"] == "A5",
        }
        for i in itens
    ]
    r = client.put("/admin/configuracoes", json={"configuracoes": novo}, headers=admin_headers)
    assert r.status_code == 204, r.text
    itens = client.get("/admin/configuracoes", headers=admin_headers).json()
    assert [i["agenda_id_sgg"] for i in itens if i["monitorada"]] == ["A5"]


def test_admin_rejeita_dois_padroes(client, admin_headers):
    body = {
        "configuracoes": [
            {
                "agenda_id_sgg": "A1",
                "monitorada": True,
                "agenda_encaixe_id_sgg": "A4",
                "encaixe_padrao": True,
            },
            {
                "agenda_id_sgg": "A2",
                "monitorada": True,
                "agenda_encaixe_id_sgg": "A4",
                "encaixe_padrao": True,
            },
        ]
    }
    r = client.put("/admin/configuracoes", json=body, headers=admin_headers)
    assert r.status_code == 400


def test_admin_sincronizar_e_logs(client, admin_headers):
    r = client.post("/admin/sincronizar", headers=admin_headers)
    assert r.status_code == 200 and r.json()["agendas"] == 5
    r = client.get("/admin/logs?limite=10", headers=admin_headers)
    assert r.status_code == 200 and r.json()[0]["tipo"] == "SINCRONIZACAO"
    r = client.get("/admin/sincronizacao", headers=admin_headers)
    assert r.status_code == 200 and r.json()["sucesso"] is True


def test_timestamps_de_auditoria_tem_fuso(client, admin_headers):
    client.post("/admin/sincronizar", headers=admin_headers)
    item = client.get("/admin/logs?limite=1", headers=admin_headers).json()[0]
    assert item["criado_em"].endswith("+00:00") or item["criado_em"].endswith("Z")
    st = client.get("/admin/sincronizacao", headers=admin_headers).json()
    assert st["executado_em"].endswith("+00:00") or st["executado_em"].endswith("Z")
