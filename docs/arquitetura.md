# Arquitetura

O sistema segue **arquitetura hexagonal (ports & adapters)** no backend e uma
**máquina de estados pura** no front-end do totem. O objetivo é isolar a única
incerteza real do projeto — o contrato da API do SGG — em um ponto de troca.

```
┌────────────────────────┐        ┌──────────────────────────────────────────────┐
│  Tablet (PWA kiosk)    │        │  Backend FastAPI                              │
│  /totem                │  HTTPS │  api/        routers, schemas, erros → HTTP   │
│  React + máquina de    ├───────►│  application/ casos de uso (regras do fluxo)  │
│  estados (machine.ts)  │        │  domain/     entidades, CPF, exceções, PORTAS │
├────────────────────────┤        │  infrastructure/                              │
│  Painel /admin (JWT)   ├───────►│    sgg/  FakeGateway | HttpGateway ──► SGG    │
└────────────────────────┘        │    persistence/ SQLAlchemy + UnitOfWork ─► PG │
                                  │    scheduler.py  sync periódica (RF01)        │
                                  └──────────────────────────────────────────────┘
```

## Camadas do backend (`backend/app`)

| Camada | Pasta | Depende de | Conteúdo |
|---|---|---|---|
| Domínio | `domain/` | nada | `Cpf` (validação + máscara), `Paciente`, `Agenda`, `Agendamento`, `ConfiguracaoAgenda`, `LogOperacao`; exceções com mensagens seguras para tela pública; **portas** `SggGateway`, repositórios, `UnitOfWork`, `Clock`. |
| Aplicação | `application/` | domínio | Um caso de uso por operação do documento: `SincronizarAgendas` (RF01), `IdentificarPaciente` (RF05–07, RF10), `RealizarCheckin` (RF08–09), `Listar/SalvarConfiguracoes` (RF02–03), `ListarLogs`. |
| Infraestrutura | `infrastructure/` | domínio | `SggFakeGateway` (memória), `SggHttpGateway` + `mappers.py` (API real), repositórios SQLAlchemy, `SqlAlchemyUnitOfWork`, `SyncScheduler`. |
| API | `api/` | aplicação | `container.py` (composition root), `deps.py` (JWT admin, chave do totem), `schemas.py` (Pydantic), routers `totem`, `admin`, `health`, `errors.py` (exceção de domínio → HTTP). |

Regras que valem a pena conhecer:

* **Somente agendas monitoradas** são consultadas (RF02).
* Se o agendamento do dia está `AGENDADO` → vira `AGUARDANDO` (RF08).
* Se já está `AGUARDANDO`/`EM_ATENDIMENTO` → `409 CHECKIN_JA_REALIZADO` (não duplica).
* Sem agendamento → cria encaixe na agenda de encaixe **padrão**; se nenhuma for padrão,
  usa a primeira agenda monitorada que tenha encaixe (RF09). O encaixe já nasce `AGUARDANDO`.
* Paciente inexistente → `404 PACIENTE_NAO_ENCONTRADO` com orientação para a recepção (RF10).
* Toda operação grava `logs_operacao` com o **CPF mascarado** (auditabilidade + privacidade).

## Adaptador da API real do SGG

`infrastructure/sgg/http_gateway.py` implementa a API v3 (`https://app.sgg.net.br/api/v3/`).
Particularidades verificadas contra a API real:

* Basic Auth com a chave como usuário e senha vazia.
* Consultas são `GET` com corpo JSON e `paginador` (máx. 100 por página); o gateway percorre todas as páginas.
* Erros e retorno vazio chegam com HTTP 200: o que vale é `statusCode` (`D000` ok, `D001` vazio, demais = erro).
* Escritas devolvem `returnInfo` como *string JSON* com `{codigo,msg}` ou `{erro,msg}`; recusa vira `SggOperacaoRecusadaError` (HTTP 409 para o totem, que orienta o paciente à recepção).
* Agendamentos referenciam a agenda pelo nome; o gateway mantém um mapa nome ⇄ id, renovado a cada sincronização.
* `POST /agendamento/` exige `id_empresa`, por isso `Paciente` carrega `empresa_id_sgg`.
* Agendas por hora marcada exigem `hora_agendamento` alinhada à grade; o gateway arredonda para o próximo múltiplo da duração padrão. Agendas por ordem de chegada não recebem hora (recomendadas como encaixe).
* HTTP 429 (limite de requisições) e códigos `A*`/`S*` viram `SggIndisponivelError` (HTTP 503), sem travar o totem.
* **Resposta de escrita é JSON malformado**: o SGG embute o `returnInfo` sem escape
  (`{"returnInfo":"{"codigo":1,...}","statusCode":"D000"}`). `mappers.parse_resposta` extrai o objeto
  interno por regex antes de decodificar. Sem isso, toda escrita pareceria falhar mesmo tendo sido executada.
* `D000` sem `resultado` numa consulta é tratado como falha (não como "vazio", que é `D001`).
* Regra do SGG (D16026): um funcionário não pode ter dois agendamentos por ordem de chegada na
  mesma agenda no mesmo dia, mesmo que o anterior esteja Cancelado. O totem responde com
  `409 SGG_RECUSOU` e orienta o paciente à recepção; a recusa fica na auditoria.

Validação feita contra a API real em 17/09/2026 na unidade "TESTES AGENDA" (agendas "TESTE TI",
ordem de chegada, e "TESTE TI 2", hora marcada): sincronização, busca por CPF, listagem do dia,
criação de encaixe (`POST`) e mudança de situação (`PUT`).

## Front-end (`frontend/src`)

* `features/totem/machine.ts` — reducer puro com todas as telas e transições (RF04→RF11).
  Fácil de testar e de raciocinar; os efeitos (chamadas HTTP, timers) ficam em `TotemApp.tsx`.
* `features/totem/screens/*` — uma tela por estado; fontes grandes, poucos toques, teclado numérico próprio.
* `features/admin/*` — login, tabela de agendas (monitorar + encaixe + padrão) e auditoria.
* `api/client.ts` — `ApiError` tipado (`codigo`, `mensagem`, `status`) para as telas decidirem o que mostrar.
* PWA (`vite-plugin-pwa`) em modo `fullscreen`; a API nunca é cacheada (`NetworkOnly`).

## Banco de dados

Tabelas: `agendas`, `locais_atendimento`, `configuracoes_agenda`, `logs_operacao`, `sincronizacoes`.
Migrações com Alembic (`backend/alembic`). Em desenvolvimento, `AUTO_CREATE_SCHEMA=true` cria o schema
automaticamente em SQLite; em produção use PostgreSQL e `alembic upgrade head` (o Dockerfile já faz isso).
