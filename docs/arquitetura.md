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
| Domínio | `domain/` | nada | `Cpf` (validação + máscara), `Paciente`, `Agenda`, `Agendamento`, `ConfiguracaoAgenda`, `ConfiguracaoGuiches`, `LogOperacao`; exceções com mensagens seguras para tela pública; **portas** `SggGateway`, repositórios, `UnitOfWork`, `Clock`. |
| Aplicação | `application/` | domínio | Um caso de uso por operação do documento: `SincronizarAgendas` (RF01), `IdentificarPaciente` (RF05–07, RF10), `RealizarCheckin` (RF08–09), `Listar/SalvarConfiguracoes` (RF02), `Obter/SalvarGuiches`, `ListarLogs`. |
| Infraestrutura | `infrastructure/` | domínio | `SggFakeGateway` (memória), `SggHttpGateway` + `mappers.py` (API real), repositórios SQLAlchemy, `SqlAlchemyUnitOfWork`, `SyncScheduler`. |
| API | `api/` | aplicação | `container.py` (composition root), `deps.py` (JWT admin, chave do totem), `schemas.py` (Pydantic), routers `totem`, `admin`, `health`, `errors.py` (exceção de domínio → HTTP). |

Regras que valem a pena conhecer:

* **Somente agendas monitoradas** (e os dois guichês) são consultadas (RF02).
* O check-in **sempre cria um novo registro** num dos dois guichês, já `AGUARDANDO` — nunca
  altera o agendamento original (RF08/RF09). O paciente vê o horário/agenda originais na
  confirmação; o guichê é onde a recepção acompanha as chegadas. Veja **Guichês de
  atendimento** abaixo para a regra de distribuição entre os dois.
* Já existe um registro `AGUARDANDO`/`EM_ATENDIMENTO` hoje (em qualquer guichê) →
  `409 CHECKIN_JA_REALIZADO` (não duplica).
* Nenhum guichê configurado → `409 ENCAIXE_NAO_CONFIGURADO`, mesmo havendo agendamento — pelo
  menos o Guichê 1 é sempre obrigatório agora.
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
* A paginação do SGG não é confiável: a página 0 pode trazer mais linhas que o `tamanho` pedido
  e a seguinte repete parte delas (observado: 217 linhas para 159 agendamentos distintos). O
  gateway deduplica por conteúdo exato e para quando uma página não traz nada novo.
* Nem todo código que começa com "A" é falha de infraestrutura: só `A000`/`A001` (chave) e
  `S000`-`S006` (servidor) são; `AG016` ("agendamento não encontrado"), por exemplo, é de negócio
  e vira `SggOperacaoRecusadaError`, não `SggIndisponivelError`.

Validação feita contra a API real em 17/09/2026 na unidade "TESTES AGENDA" (agendas "TESTE TI",
ordem de chegada, e "TESTE TI 2", hora marcada): sincronização, busca por CPF, listagem do dia,
criação de encaixe (`POST`) e mudança de situação (`PUT`).

## Front-end (`frontend/src`)

* `features/totem/machine.ts` — reducer puro com todas as telas e transições (RF04→RF11).
  Fácil de testar e de raciocinar; os efeitos (chamadas HTTP, timers) ficam em `TotemApp.tsx`.
* `features/totem/screens/*` — uma tela por estado; fontes grandes, poucos toques, teclado numérico próprio.
* `features/admin/*` — login, guichês de atendimento, tabela de agendas monitoradas e auditoria.
* `api/client.ts` — `ApiError` tipado (`codigo`, `mensagem`, `status`) para as telas decidirem o que mostrar.
* PWA (`vite-plugin-pwa`) em modo `fullscreen`; a API nunca é cacheada (`NetworkOnly`).

## Destaque de atendimentos Preferenciais

O SGG não tem campo nativo de prioridade, então o tipo de atendimento (Preferencial/Normal)
precisa se destacar por convenção em dois lugares:

* **Observação enviada ao SGG** (`realizar_checkin.py::_observacao`): Preferencial ganha o
  prefixo `[PREFERENCIAL] ` no **início** do texto — não no fim, porque listas do SGG podem
  truncar a observação e um marcador no final some primeiro. Marcador em ASCII puro (sem
  emoji/unicode) para não depender de suporte de fonte na tela do SGG. Normal não leva marcador
  (menos ruído visual quando a maioria dos atendimentos é comum). O texto sempre traz o horário
  real da chegada ao totem (`agora`), não só o horário do agendamento original — ex.:
  `Chegada via totem 08:15 - agendado 09:30 em Clínico Geral`. O separador é um hífen simples, não
  um em-dash unicode: a versão anterior usava "—" e aparecia como "?" na tela do SGG (mesmo motivo
  do marcador em ASCII puro).
* **Auditoria do painel** (`LogsPage.tsx`): linhas de Preferencial recebem uma barra vermelha à
  esquerda e fundo levemente tingido, e a coluna "Tipo" mostra um selo vermelho com estrela em
  vez de texto simples — para pular aos olhos ao rolar a lista, sem precisar ler cada linha.

**Por que não reordenar dentro do SGG:** cogitamos priorizar Preferencial ajustando o campo
`senha` do agendamento (a API aceita `PUT` nele). Descartado: confirmado com a operação que a
tela de chamada do SGG segue a ordem de chegada/criação do registro, não o número da senha — e a
API não permite definir a hora de criação. Não há alavanca dentro de uma agenda para fazer
alguém "furar a fila"; a única forma real de priorizar é o Guichê 1 dedicado, abaixo.

## Guichês de atendimento

Motivação operacional: o SGG só permite uma pessoa "Em Atendimento" por agenda ao mesmo tempo.
Com dois atendentes numa única agenda, um atendimento longo trava o outro atendente, que não
consegue chamar o próximo. A solução é ter **duas agendas por ordem de chegada no SGG, uma por
guichê físico**, e o totem decide para qual das duas cada check-in vai.

Diferente do antigo modelo por agenda monitorada (removido), os guichês são **globais e únicos**:
todo paciente passa por um dos dois, não importa em qual agenda estava agendado. Configuração em
`ConfiguracaoGuiches` (tabela `configuracao_guiches`, linha única) — dois dropdowns no painel
(`GuichesCard` em `ConfigPage.tsx`), restritos a agendas ativas por ordem de chegada.

Distribuição (`RealizarCheckinUseCase._resolver_guiche`):

1. **Preferencial vai sempre para o Guichê 1.** Não participa do balanceamento por carga —
   por isso não pode substituir sozinho o destaque textual/visual da seção acima: se o Guichê 1
   estiver mais carregado, o preferencial ainda vai para lá, só que priorizado ali dentro pelo
   destaque visual/manual da equipe, não por reordenação automática do SGG (ver nota acima).
2. **Normal vai para o guichê com menos gente `AGUARDANDO` agora** — consulta ao vivo ao SGG
   (`listar_agendamentos_da_agenda`, mesma leitura reintroduzida por este motivo depois de ter
   sido removida junto com a funcionalidade de encaixe automático periódico). Em caso de empate,
   alterna com o último guichê escolhido (round-robin), persistido em
   `ConfiguracaoGuiches.ultimo_guiche_usado`.
3. **Com um único guichê configurado**, todo mundo vai para ele, sem consulta extra ao SGG.
4. **Sincronização** limpa sozinho um guichê cujo destino tenha sido excluído ou inativado no
   SGG, do mesmo jeito que já fazia para o encaixe por agenda monitorada.

Guichês reais confirmados no SGG do totem em produção: "Recepção" e "Guichê 2", ambas por ordem
de chegada.

## Banco de dados

Tabelas: `agendas`, `locais_atendimento`, `configuracoes_agenda`, `configuracao_guiches`,
`logs_operacao`, `sincronizacoes`. Migrações com Alembic (`backend/alembic`); a revisão "0002" foi
deliberadamente pulada (veja o comentário em `0003_guiches.py`). Em desenvolvimento,
`AUTO_CREATE_SCHEMA=true` cria o schema automaticamente em SQLite; em produção use PostgreSQL e
`alembic upgrade head` (o Dockerfile já faz isso).
