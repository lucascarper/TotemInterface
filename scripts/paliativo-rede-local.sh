#!/usr/bin/env bash
# Paliativo: roda o totem neste Mac, acessível pela rede local (tablet da recepção),
# enquanto a hospedagem na nuvem não está disponível. Sem Docker.
#
# Uso:  scripts/paliativo-rede-local.sh        (Ctrl+C para parar)
# Pré-requisito: a chave nova do SGG em backend/.env (SGG_API_KEY).
set -euo pipefail
cd "$(dirname "$0")/.."

IP="${IP:-$(ipconfig getifaddr en0 || ipconfig getifaddr en1)}"
API_PORT="${API_PORT:-8010}"
WEB_PORT="${WEB_PORT:-8080}"

# Variáveis de ambiente têm prioridade sobre backend/.env.
export APP_ENV=production SGG_MODE=http AUTO_CREATE_SCHEMA=true
export CORS_ORIGINS="http://${IP}:${WEB_PORT}"
# Segredo de sessão novo a cada execução (só invalida o login do painel ao reiniciar).
export JWT_SECRET="${JWT_SECRET_PALIATIVO:-$(openssl rand -hex 32)}"

echo "==> Gerando a tela do totem apontando para http://${IP}:${API_PORT}"
(cd frontend && VITE_API_BASE_URL="http://${IP}:${API_PORT}" npm run build >/dev/null)

pids=()
parar() { kill "${pids[@]}" 2>/dev/null || true; }
trap parar EXIT INT TERM

(cd backend && exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$API_PORT") &
pids+=($!)
(cd frontend && exec npx vite preview --host 0.0.0.0 --port "$WEB_PORT" --strictPort) &
pids+=($!)
# Impede o Mac de dormir enquanto o paliativo estiver no ar.
caffeinate -dimsu &
pids+=($!)

echo
echo "==> Totem:  http://${IP}:${WEB_PORT}/totem"
echo "==> Painel: http://${IP}:${WEB_PORT}/admin"
echo "    (Ctrl+C para parar)"
wait
