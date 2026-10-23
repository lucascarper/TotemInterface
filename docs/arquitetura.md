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
| Domínio | `domain/` | nada | `Cpf` (validação + máscara), `Paciente`, `Agenda`, `Agendamento`, `ConfiguracaoAgenda`, `ConfiguracaoTotem` (modo, agendas da recepção, encaixe), `LogOperacao`; exceções com mensagens seguras para tela pública; **portas** `SggGateway`, repositórios, `UnitOfWork`, `Clock`. |
| Aplicação | `application/` | domínio | Um caso de uso por operação do documento: `SincronizarAgendas` (RF01), `IdentificarPaciente` (RF05–07, RF10), `RealizarCheckin` (RF08–09), `Listar/SalvarConfiguracoes` (RF02), `Obter/SalvarConfiguracaoTotem`, `LimparDados`, `ListarLogs`. |
| Infraestrutura | `infrastructure/` | domínio | `SggFakeGateway` (memória), `SggHttpGateway` + `mappers.py` (API real), repositórios SQLAlchemy, `SqlAlchemyUnitOfWork`, `Agendador` (sincronização e limpeza diária). |
| API | `api/` | aplicação | `container.py` (composition root), `deps.py` (JWT admin, chave do totem), `schemas.py` (Pydantic), routers `totem`, `admin`, `health`, `errors.py` (exceção de domínio → HTTP). |

Regras que valem a pena conhecer:

* **Dois modos de check-in**, escolhidos no painel (`ModoTotem`, padrão: criação). As **agendas da
  recepção** são uma lista ordenada única, usada pelos dois modos, e aceitam ordem de chegada ou
  hora marcada.
* **Modo de criação** (o original): consulta as agendas monitoradas e as da recepção, e **sempre
  cria um novo registro** numa agenda da recepção, já `AGUARDANDO`, sem alterar o agendamento
  original (RF08/RF09). O paciente vê o horário/agenda originais na confirmação. Veja **Agendas da
  recepção** abaixo para a distribuição.
* **Modo de edição**: consulta só as agendas da recepção (as monitoradas ficam salvas, mas são
  ignoradas). O **primeiro agendamento `AGENDADO` do dia** ali vira `AGUARDANDO`, e nada é criado.
  Sem agendamento `AGENDADO` (inclusive Faltou, Cancelado ou já atendido que voltou), cria o encaixe
  na **agenda de encaixe** (por ordem de chegada, obrigatória neste modo), já `AGUARDANDO`. Como o
  `PUT` do SGG só altera `situacao`, o Preferencial de um agendamento editado aparece só na auditoria.
* Chegada que **ainda não foi atendida** → `409 CHECKIN_JA_REALIZADO` (não duplica). Na criação:
  registro da recepção em qualquer status diferente de `ATENDIDO` e `AGENDADO` (Agendado na recepção
  é agendamento marcado com antecedência, não chegada). Na edição: agendamento da recepção
  `AGUARDANDO`/`EM_ATENDIMENTO` ou registro na agenda de encaixe ainda não atendido. Vale também o
  que foi feito antes de trocar o modo.
* Registro já `ATENDIDO` não bloqueia: o paciente que sai e volta é atendido de novo. Na criação, a
  nova chegada vai para uma agenda da recepção **onde ele ainda não tem registro hoje** (o SGG recusa,
  D16026, dois registros do mesmo paciente na mesma agenda de ordem de chegada no mesmo dia). Na
  edição, vai para a agenda de encaixe, que só aceita um por dia. Sem destino possível, ou sem agenda
  da recepção configurada → `409 ENCAIXE_NAO_CONFIGURADO`, orientando a recepção.
* No modo de criação, o registro nasce **no mesmo funcionário e na mesma empresa do agendamento encontrado**
  nas agendas de consultório (o agendamento traz `id_funcionario` e `id_empresa`). A busca do
  agendamento do dia cobre todos os vínculos do CPF, não só o preferido. Sem agendamento
  (encaixe), vale o vínculo preferido.
* Empresa que será usada inativa no SGG (e, sem agendamento, nenhum outro vínculo do CPF numa
  empresa ativa) → `409 EMPRESA_INATIVA`, sem criar nem editar nada. Veja o vínculo no adaptador
  do SGG abaixo.
* Paciente inexistente → `404 PACIENTE_NAO_ENCONTRADO` com orientação para a recepção (RF10).
* Toda operação grava `logs_operacao` com o **CPF mascarado** (auditabilidade + privacidade). A
  troca de modo também é registrada, com o usuário que trocou.
* **Limpeza diária** (`LimparDados`, às 03:00 e ao iniciar a API): apaga eventos mais antigos que
  `RETENCAO_LOGS_DIAS` (padrão 30) e agendas inativas que não estão em nenhuma configuração; no
  SQLite compacta o arquivo (`VACUUM`) ao iniciar e aos domingos. Sincronização bem-sucedida não vai
  para a auditoria, e `sincronizacoes` guarda só a última execução. O agendador roda uma rotina de
  cada vez (o `VACUUM` falha com outra transação aberta).

## Adaptador da API real do SGG

`infrastructure/sgg/http_gateway.py` implementa a API v3 (`https://app.sgg.net.br/api/v3/`).
Particularidades verificadas contra a API real:

* Basic Auth com a chave como usuário e senha vazia.
* Consultas são `GET` com corpo JSON e `paginador` (máx. 100 por página); o gateway percorre todas as páginas.
* Erros e retorno vazio chegam com HTTP 200: o que vale é `statusCode` (`D000` ok, `D001` vazio, demais = erro).
* Escritas devolvem `returnInfo` como *string JSON* com `{codigo,msg}` ou `{erro,msg}`; recusa vira `SggOperacaoRecusadaError` (HTTP 409 para o totem, que orienta o paciente à recepção).
* Agendamentos referenciam a agenda pelo nome; o gateway mantém um mapa nome ⇄ id, renovado a cada sincronização.
* Um CPF pode ter vários vínculos (`funcionario/`), um por empresa, inclusive empresas antigas já
  inativas. `buscar_paciente_por_cpf` devolve o vínculo preferido (cuja empresa esteja ativa,
  depois funcionário `Ativo` e o editado mais recentemente) junto com o mapa de todos os vínculos
  (`Paciente.vinculos`). Quem decide se a empresa **usada** está ativa é o caso de uso, pela porta
  `empresa_ativa(id)`: consulta `empresa/` com o filtro `codigo` (o filtro `id_empresa` é
  ignorado e devolveria as ~2.300 empresas) e vale `situacao` = `ativa`; inexistente, sem
  `id_empresa` ou qualquer outro valor conta como inativa. O resultado fica em cache por 5 minutos
  (`TTL_EMPRESA_SEGUNDOS`; falhas não entram no cache), pois a identificação e o check-in
  consultam as mesmas empresas e o SGG limita requisições.
* A busca do agendamento do dia roda em paralelo, uma consulta por vínculo do CPF. A identificação
  já avisa `EMPRESA_INATIVA` antes de o paciente confirmar; quem já está na fila segue para
  "chegada já registrada".
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
* `features/admin/*` — login, configuração do totem (`TotemCard`: modo, agendas da recepção e encaixe), tabela de agendas monitoradas e auditoria.
* `api/client.ts` — `ApiError` tipado (`codigo`, `mensagem`, `status`) para as telas decidirem o que mostrar.
* PWA (`vite-plugin-pwa`) em modo `fullscreen`; a API nunca é cacheada (`NetworkOnly`).

### Ajuste ao tablet da recepção (sem rolagem)

O tablet físico usado na recepção tem tela de 8,7" e resolução 1920×1200, mas o navegador
reporta uma viewport CSS bem menor (o Android aplica um `devicePixelRatio` alto nesse
tamanho de painel). Em orientação paisagem isso pode significar uma altura útil de ~600px
CSS, e o layout original (alturas fixas em `rem` para teclado, cartões e botões) não cabia
nesse espaço — daí os pacientes precisarem rolar a tela.

Correção: `KioskShell` fixa a altura em `100dvh` com `overflow-hidden` (nunca rola a página
inteira) e o cabeçalho/rodapé usam `clamp(mínimo, Ndvh, máximo)` para encolher em telas
baixas. Na tela de CPF (`CpfScreen`), o teclado numérico deixou de ter altura fixa por tecla
e passou a ser um grid com `flex-1` + `grid-rows-4`, ocupando exatamente o espaço que sobrar
depois do cabeçalho, do CPF digitado e do botão "Continuar" — funciona em qualquer altura de
viewport sem precisar acertar valores manualmente. As demais telas (`ConfirmScreen`,
`SuccessScreen`, `ErrorScreen`) tiveram margens/paddings/ícones reduzidos para caber no
mesmo orçamento vertical, mantendo o tamanho do texto (importante para pacientes
idosos/preferenciais) e reduzindo o que é só espaçamento decorativo.

### Linguagem visual do totem

O tablet fica em **paisagem**. Em telas a partir de `md` (768px), CPF e Confirmação usam duas
colunas: na tela de CPF o teclado ocupa a altura toda à direita (teclas de ~117px em 960x600,
contra ~46px em coluna única); em telas estreitas tudo volta a uma coluna. Estilo claro e
clínico: fundo `surface-alt`, superfícies brancas com contorno fino (`.panel`), um único raio
(`rounded-xl2`) para botões, teclas e cartões, azul da marca como única cor de ação (vermelho só
para Preferencial e erros, verde só para sucesso). Ícones da biblioteca Phosphor em peso
`bold` (`components/Icons.tsx`). Animações só de entrada e retorno ao toque, desligadas com
`prefers-reduced-motion`.

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
alguém "furar a fila"; a única forma real de priorizar é a 1ª agenda da recepção, abaixo.

## Agendas da recepção

Motivação operacional: o SGG só permite uma pessoa "Em Atendimento" por agenda ao mesmo tempo.
Com dois atendentes numa única agenda, um atendimento longo trava o outro, que não consegue chamar
o próximo. Por isso a recepção tem **uma agenda por guichê físico**, quantas forem necessárias, e no
modo de criação o totem decide para qual cada check-in vai. A lista substituiu os dois guichês fixos
da versão anterior (migração `0004`, que leva Guichê 1 e Guichê 2 para as duas primeiras posições).

Configuração em `ConfiguracaoTotem` (tabela `configuracao_totem`, linha única), no cartão
`TotemCard` do painel. Distribuição no modo de criação (`RealizarCheckinUseCase._resolver_recepcao`):

1. **Preferencial vai para a 1ª agenda disponível da lista.** Não participa do balanceamento.
2. **Normal vai para a de menos gente `AGUARDANDO` agora** (consulta ao vivo ao SGG). No empate,
   vai para a próxima da lista depois da última usada (round-robin), persistida em
   `ConfiguracaoTotem.ultima_recepcao_usada`.
3. **Com uma única agenda disponível**, todo mundo vai para ela, sem consulta extra ao SGG.
4. **Sincronização** tira sozinha da lista (e do encaixe) uma agenda excluída ou inativada no SGG.

## Banco de dados

Tabelas: `agendas`, `locais_atendimento`, `configuracoes_agenda`, `configuracao_totem`,
`logs_operacao`, `sincronizacoes`. Migrações com Alembic (`backend/alembic`); a revisão "0002" foi
deliberadamente pulada (veja o comentário em `0003_guiches.py`). Em desenvolvimento,
`AUTO_CREATE_SCHEMA=true` cria o schema automaticamente em SQLite; em produção use PostgreSQL e
`alembic upgrade head` (o Dockerfile já faz isso). O paliativo na rede local usa `AUTO_CREATE_SCHEMA`
sobre SQLite, sem Alembic; por isso a migração de dados da `0004` (`persistence/migracoes.py`) também
roda na inicialização nesse modo. A `0003` usa `DROP COLUMN IF EXISTS`, que só o PostgreSQL entende:
a cadeia completa do Alembic não roda em SQLite.
