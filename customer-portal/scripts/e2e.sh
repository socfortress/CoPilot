#!/usr/bin/env bash
# Browser e2e for the Customer Portal (#1181): starts the backend against the
# disposable e2e MySQL and a dedicated portal dev server, runs Cypress, stops both.
#
#   pnpm test:e2e         # headless
#   pnpm test:e2e:open    # Cypress UI
#
# Needs the e2e MySQL on 127.0.0.1:13306 — see cypress/README.md for the one-line
# docker run. Everything is overridable through E2E_* variables; the database ones are
# deliberately NOT read from MYSQL_* so a shell pointed at a real CoPilot cannot be
# seeded by accident.
set -euo pipefail

PORTAL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$(cd "$PORTAL_DIR/../backend" && pwd)"
API_PORT="${E2E_API_PORT:-5101}"
WEB_PORT="${E2E_WEB_PORT:-3101}"
PYTHON="${E2E_PYTHON:-$BACKEND_DIR/.venv/bin/python}"
UVICORN="${E2E_UVICORN:-$BACKEND_DIR/.venv/bin/uvicorn}"

export MYSQL_URL="${E2E_MYSQL_URL:-127.0.0.1:13306}"
export MYSQL_USER="${E2E_MYSQL_USER:-copilot}"
export MYSQL_PASSWORD="${E2E_MYSQL_PASSWORD:-e2epass}"
export MYSQL_ROOT_PASSWORD="${E2E_MYSQL_ROOT_PASSWORD:-e2eroot}"
export JWT_SECRET="${E2E_JWT_SECRET:-e2e-test-secret-not-the-default}"
export PYTHONPATH="$BACKEND_DIR"
export E2E_PYTHON="$PYTHON"

for port in "$API_PORT" "$WEB_PORT"; do
	if lsof -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
		echo "Port $port is already in use: stop what is on it or set E2E_API_PORT / E2E_WEB_PORT." >&2
		exit 1
	fi
done

wait_for() {
	local url="$1" name="$2"
	for _ in $(seq 1 60); do
		curl -sf -o /dev/null "$url" && return 0
		sleep 1
	done
	echo "$name did not come up at $url" >&2
	return 1
}

pids=()
cleanup() {
	local status=$?
	for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
	if [[ $status -ne 0 && -n "${BACKEND_LOG:-}" ]]; then echo "Backend log: $BACKEND_LOG" >&2; fi
}
trap cleanup EXIT

echo "Applying migrations to $MYSQL_URL"
(cd "$BACKEND_DIR" && "$PYTHON" -c "from app.db.db_setup import apply_migrations; apply_migrations()" >/dev/null 2>&1) || {
	echo "Could not migrate the e2e database at $MYSQL_URL — is the e2e MySQL running? See cypress/README.md." >&2
	exit 1
}

BACKEND_LOG="$(mktemp -t copilot-portal-e2e-backend.XXXXXX)"
echo "Starting the backend on :$API_PORT (no lifespan: no scheduler, MinIO or connector sync); log: $BACKEND_LOG"
(cd "$BACKEND_DIR" && exec "$UVICORN" copilot:app --lifespan off --port "$API_PORT" --log-level warning >"$BACKEND_LOG" 2>&1) &
pids+=($!)
wait_for "http://127.0.0.1:$API_PORT/api/customer_portal/settings" "The backend"

echo "Starting the portal on :$WEB_PORT"
(cd "$PORTAL_DIR" && VITE_API_URL="http://127.0.0.1:$API_PORT" exec pnpm exec vite --port "$WEB_PORT" --strictPort --logLevel warn) &
pids+=($!)
wait_for "http://localhost:$WEB_PORT/login" "The portal"

export CYPRESS_BASE_URL="http://localhost:$WEB_PORT"
if [[ "${E2E_OPEN:-}" == "1" ]]; then
	pnpm exec cypress open --e2e
else
	pnpm exec cypress run --e2e "$@"
fi
