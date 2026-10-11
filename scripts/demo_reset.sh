#!/usr/bin/env bash
# Put the demo back to its starting state without rebuilding anything or losing the embedding model.
#
#   scripts/demo_reset.sh
#
# Stops the stack, drops the data volumes (database, uploaded files, the proposal index), and
# starts it again, which re-runs the migrations and the synthetic seed. The volume holding the
# downloaded embedding model is kept, so the first search afterwards is not a 440 MB download.
set -euo pipefail
cd "$(dirname "$0")/.."

export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-campuscue}"
project="campuscue"

docker compose down
for volume in pgdata miniodata ragchroma; do
  docker volume rm "${project}_${volume}" >/dev/null 2>&1 || true
done
docker compose up -d postgres minio minio-init migrate seed-demo core-api agent-api rag-api web

echo -n "waiting for Core and the Agent "
for _ in $(seq 1 60); do
  core=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8000/ready || true)
  agent=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8001/ready || true)
  if [ "$core" = 200 ] && [ "$agent" = 200 ]; then
    echo " ready"
    break
  fi
  echo -n "."
  sleep 2
done

token=$(curl -s -X POST http://localhost:8000/api/v1/auth/demo-login \
  -H 'content-type: application/json' --data '{"email":"organizer@example.invalid"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
total=$(curl -s "http://localhost:8000/api/v1/events?limit=1" -H "authorization: Bearer $token" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["total"])')
echo "seeded events: $total (a pristine demo has 6)"
