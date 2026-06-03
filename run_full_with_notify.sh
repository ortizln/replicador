#!/usr/bin/env bash
set -euo pipefail
cd ~/replicador

set -a
source .env.full
source .env.sync
set +a

send_tg(){
  local msg="$1"
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    curl -sS -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      -d "text=${msg}" >/dev/null || true
  fi
}

start_ts="$(date '+%F %T')"
send_tg "🚀 Inicia réplica FULL ErpEpmapaT (${start_ts})"

if /usr/bin/python3 full_replicate_db.py --confirm --jobs 1 >> ~/replicador/logs/full.log 2>&1; then
  end_ts="$(date '+%F %T')"
  send_tg "✅ Finalizó réplica FULL ErpEpmapaT (${end_ts})"
else
  end_ts="$(date '+%F %T')"
  send_tg "❌ Falló réplica FULL ErpEpmapaT (${end_ts}). Revisa ~/replicador/logs/full.log"
  exit 1
fi
