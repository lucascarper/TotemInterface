# Deploy no Railway

O projeto sobe no [Railway](https://railway.com) como **três serviços** dentro
de um mesmo projeto: PostgreSQL (add-on gerenciado), a API (`backend/`) e o
front (`frontend/`). Cada serviço ganha seu próprio domínio público HTTPS, por
isso front e API são origens diferentes — a comunicação entre eles usa CORS,
diferente do deploy via `docker-compose` (que serve tudo pela mesma origem
com nginx fazendo proxy).

Arquivos preparados no repositório:

| Arquivo | Serviço | Para quê |
|---|---|---|
| `backend/Dockerfile` | api | já existente; agora respeita a variável `PORT` |
| `backend/railway.toml` | api | builder, healthcheck (`/health`), política de restart |
| `frontend/Dockerfile.railway` | web | build do Vite + `serve` (não usa nginx: escuta em `$PORT` dinamicamente) |
| `frontend/railway.toml` | web | aponta para `Dockerfile.railway`, healthcheck (`/`) |

## Pré-requisito: repositório no GitHub

O Railway integra com GitHub para deploy automático a cada push. Se o
repositório ainda não tem remoto:

```bash
gh repo create totem-recepcao --private --source=. --remote=origin
git push -u origin main
```

(Alternativa sem GitHub: instale a Railway CLI e rode `railway up` a partir de
cada pasta de serviço — mais manual, sem deploy automático em cada push.)

## 1. Criar o projeto e o banco

No [dashboard do Railway](https://railway.com/new):

1. **New Project → Deploy PostgreSQL**. Isso cria o serviço `Postgres` com a
   variável `DATABASE_URL` pronta para ser referenciada pelos outros serviços.

## 2. Serviço da API

1. No mesmo projeto: **New → GitHub Repo** → selecione o repositório.
2. Em **Settings → Root Directory**, defina `backend`. O Railway detecta o
   Dockerfile e o `railway.toml` automaticamente.
3. Em **Variables**, adicione:

   ```
   APP_ENV=production
   LOG_LEVEL=INFO
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   AUTO_CREATE_SCHEMA=false
   SGG_MODE=http
   SGG_BASE_URL=https://app.sgg.net.br/api/v3/
   SGG_API_KEY=<sua chave real de 32 caracteres>
   SGG_TIMEOUT_SECONDS=15
   SYNC_INTERVAL_SECONDS=300
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=<troque esta senha>
   JWT_SECRET=<gere um segredo longo e aleatório>
   JWT_EXPIRES_MINUTES=480
   TOTEM_API_KEY=
   CORS_ORIGINS=https://${{web.RAILWAY_PUBLIC_DOMAIN}}
   ```

   `${{Postgres.DATABASE_URL}}` e `${{web.RAILWAY_PUBLIC_DOMAIN}}` são
   [referências de variável](https://docs.railway.com/guides/variables#referencing-another-services-variable)
   do Railway: ele resolve sozinho o valor do outro serviço, inclusive quando
   o domínio mudar. O serviço `web` precisa existir antes dessa referência
   funcionar — veja a seção **Ordem de bootstrap** abaixo se preferir a
   variável fixa em vez da referência.

4. Deploy. Em **Settings → Networking → Generate Domain** para obter a URL
   pública da API (algo como `https://api-production-xxxx.up.railway.app`).

## 3. Serviço do front

1. **New → GitHub Repo** → mesmo repositório novamente.
2. **Settings → Root Directory**: `frontend`.
3. Confirme em **Settings → Build** que o Dockerfile usado é
   `Dockerfile.railway` (o `railway.toml` já aponta para ele; se o Railway não
   ler o arquivo automaticamente, defina o caminho manualmente nessa tela).
4. Em **Variables** (variáveis de **build**, usadas pelo Vite):

   ```
   VITE_API_BASE_URL=https://${{api.RAILWAY_PUBLIC_DOMAIN}}
   VITE_TOTEM_API_KEY=
   ```

5. Deploy. Em **Settings → Networking → Generate Domain** para obter a URL
   pública do totem, por exemplo `https://web-production-xxxx.up.railway.app`.

## Ordem de bootstrap

As variáveis `CORS_ORIGINS` (na api) e `VITE_API_BASE_URL` (no web) referenciam
o domínio um do outro. Na primeira vez, nenhum dos dois existe ainda. Duas
formas de resolver:

- **Com referências de variável** (como acima): configure ambos os serviços
  com as referências `${{...}}`, faça o primeiro deploy de cada um (o valor
  fica vazio/inválido nesse primeiro deploy), e depois **redeploy os dois**
  uma segunda vez — nesse ponto os domínios já existem e as referências
  resolvem corretamente.
- **Com valores fixos**: deploy a api primeiro, copie o domínio gerado e cole
  literalmente em `VITE_API_BASE_URL` no web; deploy o web, copie o domínio
  gerado e cole literalmente em `CORS_ORIGINS` na api; redeploy a api.

## 4. Acessando

- Totem: `https://<domínio do web>/totem`
- Painel: `https://<domínio do web>/admin`

No tablet, abra o totem no navegador e use "Adicionar à tela inicial" para
rodar em modo PWA de tela cheia.

## 5. Configurar as agendas no painel (obrigatório)

O banco do Railway começa vazio: a configuração feita em desenvolvimento
(SQLite local) **não é levada** para lá. Sem este passo o totem não consulta
nenhuma agenda e, sem agendamento, não sabe onde criar o encaixe. O check-in
falha com HTTP 409 e a tela "Não foi possível registrar".

1. Entre em `https://<domínio do web>/admin` e clique em **Sincronizar com o SGG**.
2. Marque as agendas a monitorar e escolha a **agenda de encaixe** de cada uma.
3. Marque uma delas como **encaixe padrão** e clique em **Salvar alterações**.

Para diagnosticar uma falha no check-in, abra a aba **Auditoria** do painel:
"Sem agenda de encaixe configurada" indica este passo pendente, enquanto
"SGG recusou: ..." traz o código de erro devolvido pelo SGG.

## Atualizações seguintes

Cada `git push` para a branch conectada dispara um novo deploy automático dos
dois serviços (ou só do que mudou, se você configurar "Watch Paths" em
**Settings → Build** para cada serviço apontando para `backend/**` ou
`frontend/**` — evita rebuildar os dois a cada commit).

## Decisões deste deploy

- **Banco de dados: sempre PostgreSQL, nunca SQLite.** O sistema de arquivos
  de um serviço Railway é efêmero — qualquer arquivo local (incluindo um
  `totem.db` do SQLite) é perdido a cada novo deploy ou reinício do
  container. `DATABASE_URL` normaliza sozinho `postgres://` e `postgresql://`
  (formatos que o Railway costuma injetar) para o driver `psycopg` (v3) que
  este projeto usa — não é preciso editar a URL manualmente.
- **Front sem nginx**: como cada serviço Railway já tem seu próprio domínio
  público, o proxy same-origin do `frontend/Dockerfile` (usado no
  docker-compose) não se aplica aqui. `Dockerfile.railway` builda o front e
  serve os arquivos estáticos com `serve`, escutando na porta dinâmica que o
  Railway injeta (`$PORT`) — nginx exigiria um passo extra de template para
  isso, que o `serve` já faz nativamente.
- **CORS cross-origin**: como front e API ficam em domínios diferentes, o
  `CORS_ORIGINS` da API precisa listar o domínio do front. Fora do
  `APP_ENV=development`, o backend não aceita origens fora dessa lista (veja
  `backend/app/core/config.py`).
- **Health checks**: `backend/railway.toml` aponta para `/health` (já
  implementado). `frontend/railway.toml` aponta para `/`, servido pelo
  `serve`.
- **Limite de plano**: no plano gratuito do Railway os serviços podem
  hibernar após um período sem tráfego; a sincronização periódica com o SGG
  só roda enquanto o serviço da API estiver ativo.

## Se preferir Docker Compose em vez do Railway

O `docker-compose.yml` na raiz continua funcionando como está (PostgreSQL +
API + nginx na mesma origem) para rodar em qualquer host com Docker — use-o
se decidir hospedar em uma VPS própria em vez do Railway.
