# Deployment (AI Agent View)

Source of truth: `docker-compose.yml`.

## Runtime Services

| Service | Compose Name | Purpose | Exposed Ports | Persistent Storage |
|---|---|---|---|---|
| Backend API | `copilot-backend` | FastAPI app (`/api/*`) | `5000:5000` | `./data/copilot-backend-data/logs:/opt/logs`, `./data/data:/opt/copilot/backend/data` |
| Frontend (Nginx) | `copilot-frontend` | UI + TLS termination + reverse proxy to backend | `80:80`, `443:443` | none by default |
| MySQL | `copilot-mysql` | Primary relational DB | `3306:3306` | named volume `mysql-data:/var/lib/mysql` |
| MinIO | `copilot-minio` | Object storage for case/artifact files | `9000:9000` (S3 API), container also uses `9001` console | `./data/data/minio-data:/data` |
| Nuclei module | `copilot-nuclei-module` | External module container | none | none |
| MCP service | `copilot-mcp` | MCP/OpenAI-adjacent service + optional subservers | none exposed by compose | `./data/copilot-mcp/api.config.yaml:/app/velociraptor-config.yaml:ro` |
| Customer portal (optional) | `copilot-customer-portal` | Separate customer-facing UI | example `8443:443` (commented) | none by default |

## Networking and Request Path

- Browser -> `copilot-frontend` :443
- `copilot-frontend` proxies `/api` to `http://copilot-backend:5000` (see `frontend/build/etc/nginx/sites-enabled/default.conf`)
- Backend connects internally to:
  - MySQL via env (`MYSQL_URL`, defaults to `copilot-mysql`)
  - MinIO via env (`MINIO_URL`, defaults to `copilot-minio`)

## Environment Variable Overview

Primary env file: `.env` (template: `.env.example`).

- Core runtime:
  - `SERVER_IP`, `SERVER_HOST`
- MySQL:
  - `MYSQL_URL`, `MYSQL_ROOT_PASSWORD`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`
- MinIO:
  - `MINIO_URL`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `MINIO_SECURE`
- Connector bootstrap values:
  - e.g. `WAZUH_INDEXER_URL`, `GRAYLOG_URL`, `GRAFANA_URL`, etc. (loaded in `backend/app/db/db_populate.py`)
- Header/shared-secret style values:
  - `GRAYLOG_API_HEADER_VALUE`, `VELOCIRAPTOR_API_HEADER_VALUE`
- MCP/OpenAI values:
  - `OPENAI_API_KEY`, `OPENAI_MODEL`, `MCP_*`, `OPENSEARCH_*`, `WAZUH_PROD_*`, `VELOCIRAPTOR_*`

## TLS

Frontend TLS behavior is implemented in:
- `frontend/build/docker-entrypoint.d/90-copilot-ssl.sh`
- `frontend/build/etc/nginx/sites-enabled/default.conf`

Behavior:
- If `TLS_CERT_PATH`/`TLS_KEY_PATH` files exist, Nginx uses them.
- If missing, startup script auto-generates self-signed certs (365 days).
- Port 80 redirects to HTTPS (443).

## Persistence Model

- MySQL durable data:
  - Docker named volume `mysql-data`.
- MinIO durable objects:
  - Host path `./data/data/minio-data`.
- Backend local files/logs:
  - Host paths under `./data/...` bind-mounted into backend.
- Buckets auto-created at startup:
  - See `backend/app/data_store/data_store_setup.py` (`copilot-cases`, `copilot-case-report-templates`, `sysmon-configs`, `velociraptor-artifacts`).

## Startup Initialization Hooks (Deployment-Relevant)

`backend/copilot.py` startup event performs:
- DB creation/user bootstrap in production
- Alembic migrations (`backend/app/db/db_setup.py`)
- MinIO bucket creation
- connector + integration seed data
- admin/scheduler user ensure
- scheduler init/start

If deployment seems healthy but features fail, validate this startup chain first.
