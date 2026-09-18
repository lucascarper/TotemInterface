<p align="center"><img src="frontend/public/brand/logo-multilife.png" alt="MultiLife" width="360"></p>

# Totem de Recepção · Integração SGG

Autoatendimento em tablet para a recepção MultiLife: o paciente informa o CPF, confirma os dados e
tem a chegada registrada no SGG (Agendado → Aguardando) ou é incluído na agenda de encaixe.
Especificação completa em [`docs/especificacao.md`](docs/especificacao.md); decisões de projeto em
[`docs/arquitetura.md`](docs/arquitetura.md).

## Stack

| Camada | Tecnologia |
|---|---|
| Totem + painel | React 18, TypeScript, Vite, Tailwind, PWA (modo fullscreen) |
| API intermediária | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, httpx, PyJWT |
| Banco | PostgreSQL (produção) · SQLite (desenvolvimento) |
| Integração | `SggGateway` (porta) com adaptadores `fake` (memória) e `http` (API real) |

## Rodando em desenvolvimento

```bash
# 1. Backend (SQLite + SGG simulado)
cd backend
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
cp ../.env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8000
```

```bash
# 2. Frontend
cd frontend
npm install
cp .env.example .env
npm run dev
```

* Totem: <http://localhost:5173/totem>
* Painel: <http://localhost:5173/admin> (usuário `admin`, senha `admin123` — troque no `.env`)
* Swagger: <http://localhost:8000/docs>

No painel, clique em **Sincronizar com o SGG**, marque as agendas a monitorar e escolha a agenda de encaixe.

### CPFs de teste (modo `SGG_MODE=fake`)

| CPF | Paciente | Cenário |
|---|---|---|
| `529.982.247-25` | Maria Aparecida da Silva | Tem agendamento hoje → status vira *Aguardando* |
| `111.444.777-35` | João Pedro Santos | Sem agendamento → criado encaixe |
| `123.456.789-09` | Ana Beatriz Oliveira | Já *Aguardando* → aviso de chegada já registrada |
| outro CPF válido | — | Não cadastrado → orientação para a recepção |

## Testes e qualidade

```bash
cd backend && .venv/bin/pytest -q && .venv/bin/ruff check app tests
```

```bash
cd frontend && npm run build
```

## Produção no Railway

Veja o passo a passo em [`docs/deploy-railway.md`](docs/deploy-railway.md):
três serviços (PostgreSQL, API e front), cada um com seu próprio domínio
público, sem precisar de servidor próprio.

## Produção com Docker Compose (VPS própria)

```bash
cp .env.example .env   # ajuste SGG_MODE=http, SGG_BASE_URL, SGG_API_KEY, ADMIN_PASSWORD, JWT_SECRET
docker compose up -d --build
```

Sobe PostgreSQL, a API (com `alembic upgrade head`) e o front em nginx em <http://localhost:8080>.
O nginx faz proxy da API na mesma origem, então o tablet só precisa da URL do site.

### Tablet em modo kiosk

Abra `http://<servidor>:8080/totem` no navegador do tablet e use “Adicionar à tela inicial”
(PWA em tela cheia) ou o modo kiosk do Android/iPadOS. O totem volta sozinho à tela inicial
após cada atendimento e após 60 s de inatividade.

## Conectando à API real do SGG

O adaptador em `backend/app/infrastructure/sgg/http_gateway.py` implementa a
[API v3 do SGG](https://app.sgg.net.br/api/v3/doc/) e foi validado contra a API real.
Basta no `.env`:

```
SGG_MODE=http
SGG_BASE_URL=https://app.sgg.net.br/api/v3/
SGG_API_KEY=<sua chave de 32 caracteres>
```

Como o totem usa o SGG:

| Operação do totem | Chamada no SGG |
|---|---|
| Sincronizar agendas / unidades | `GET /agenda/`, `GET /unidade_atendimento/` (paginado) |
| Localizar paciente por CPF | `GET /funcionario/` com `{"cpf": "000.000.000-00"}` (prefere vínculo Ativo) |
| Agendamentos do dia | `GET /agendamento/` por `id_funcionario` e intervalo do dia, filtrando pelas agendas monitoradas |
| Agendado → Aguardando | `PUT /agendamento/` com `situacao: "Aguardando"` |
| Encaixe | `POST /agendamento/` com `id_empresa` do funcionário e o **nome** da agenda; em agendas por hora marcada envia o próximo horário da grade |

Limite da API: 60 requisições/min entre 5h e 20h (120 fora desse horário). Um check-in usa 3 a 5 chamadas.
Para testar sem afetar a operação, use a unidade "TESTES AGENDA" (agendas "TESTE TI" e "TESTE TI 2") no painel.
Preferencial/Normal vai no campo `observacoes` do agendamento, pois o SGG não tem prioridade nativa.

## Variáveis de ambiente

Veja [`.env.example`](.env.example). As principais: `DATABASE_URL`, `SGG_MODE`, `SGG_BASE_URL`,
`SGG_API_KEY`, `SYNC_INTERVAL_SECONDS`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `JWT_SECRET`,
`TOTEM_API_KEY` (opcional, exigida no header `X-Totem-Key`), `CORS_ORIGINS`.
