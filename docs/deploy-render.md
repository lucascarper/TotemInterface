# Deploy no Render

Substitui o Railway (suspenso após o incidente de segurança de 21/10/2026). O
[`render.yaml`](../render.yaml) na raiz cria tudo de uma vez:

| Recurso | O que é | Observação |
|---|---|---|
| `totem-api` | API (`backend/Dockerfile`) | Roda `alembic upgrade head` ao subir; healthcheck em `/health` |
| `totem-web` | Tela do totem e painel (`frontend/Dockerfile.railway`) | Mesmo Dockerfile do Railway: `serve` com fallback de SPA em `$PORT` |
| `totem-db` | PostgreSQL 16 gerenciado | `DATABASE_URL` vai para a API automaticamente |

Os três ficam na região `virginia` e em plano pago mínimo. No plano gratuito os
serviços dormem sem uso e a API roda a sincronização com o SGG em segundo plano.
Confira o preço na tela de criação antes de confirmar.

## Antes de começar: segredos novos

As variáveis que estavam no Railway podem ter vazado. Use valores **novos**, nunca
os antigos:

- `SGG_API_KEY`: a chave nova que você já gerou no SGG.
- `ADMIN_PASSWORD`: senha nova do painel.
- `TOTEM_API_KEY` (opcional): se usar, gere uma nova e coloque o **mesmo** valor em
  `VITE_TOTEM_API_KEY`. Se não usar, deixe as duas vazias.
- `JWT_SECRET`: o Render gera sozinho.

Revogue também o acesso do app do Railway no GitHub (Settings → Applications).

## 1. Criar pelo Blueprint

1. Crie a conta em <https://render.com> e conecte o GitHub com acesso ao
   repositório `lucascarper/TotemInterface`.
2. **New → Blueprint**, escolha o repositório e o branch `main`. O Render lê o
   `render.yaml` e lista os três recursos.
3. Ele pede os valores marcados como "preencher na criação":

   | Variável | Serviço | Valor |
   |---|---|---|
   | `SGG_API_KEY` | totem-api | chave nova do SGG |
   | `ADMIN_PASSWORD` | totem-api | senha nova do painel |
   | `TOTEM_API_KEY` | totem-api | vazio, ou a chave do totem |
   | `CORS_ORIGINS` | totem-api | `https://totem-web.onrender.com` |
   | `VITE_API_BASE_URL` | totem-web | `https://totem-api.onrender.com` |
   | `VITE_TOTEM_API_KEY` | totem-web | vazio, ou o mesmo valor de `TOTEM_API_KEY` |

4. **Apply**. O primeiro build leva alguns minutos.

## 2. Conferir as URLs reais

Se o nome `totem-api` ou `totem-web` já existir no Render, ele acrescenta um sufixo
à URL. Abra cada serviço e copie a URL que aparece no topo. Se for diferente da
que você preencheu:

1. Em **totem-api → Environment**, ajuste `CORS_ORIGINS` para a URL real do front.
2. Em **totem-web → Environment**, ajuste `VITE_API_BASE_URL` para a URL real da API.
3. Em **totem-web → Manual Deploy → Deploy latest commit**. O front grava essa URL
   no build, então só mudar a variável não basta.

## 3. Validar

- `https://<url-da-api>/health` responde `{"status":"ok","sgg_mode":"http"}`.
- `https://<url-do-front>/admin`: entre, clique em **Sincronizar com o SGG**, marque
  as agendas monitoradas e configure as agendas da recepção. O banco é novo; a configuração do
  Railway não vem junto.
- `https://<url-do-front>/totem`: faça um check-in de teste.
- No tablet, abra a URL nova do totem (e reinstale o atalho/PWA, se usava).

## 4. Desligar o paliativo e o Railway

Com o Render validado, pare o paliativo do Mac (Ctrl+C no Terminal). Depois que o
Railway voltar, apague o projeto de lá, que ainda guarda os segredos antigos.

## Atualizações

Cada push no `main` faz o Render reconstruir os dois serviços. Mudanças no
`render.yaml` são aplicadas em **Blueprints → totem → Sync**.
