# Cloud Run Deployment Notes

## Status

**Not yet deployable.** No Dockerfile or container definition exists in this repo. The workflow (`deploy-cloud-run.yml`) and this config spec are scaffolding for a planned deployment.

To make this functional, you need:
1. A `Dockerfile` in the repo root
2. GitHub repository variables and secrets configured (listed below)
3. GCP project with Cloud Run, Secret Manager, and Artifact Registry enabled

---

This repo ships a private operator runtime in [`runtime/app.py`](../../runtime/app.py).

## Required GitHub Repository Variables

- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GAR_LOCATION`
- `GAR_REPOSITORY`
- `CLOUD_RUN_STAGING_SERVICE`
- `CLOUD_RUN_PRODUCTION_SERVICE`
- `CLOUD_RUN_RUNTIME_SERVICE_ACCOUNT`

## Required GitHub Secrets

- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOY_SERVICE_ACCOUNT`

## Required GCP Secret Manager Secrets

The deploy workflow assumes these secret names exist in Secret Manager and are injected into Cloud Run with matching environment variable names:

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `VERTEX_API_KEY`

## Runtime Defaults

- Authenticated-only Cloud Run service
- Production deploy settings:
  - `min-instances=1`
  - `max-instances=10`
  - `concurrency=4`
  - `timeout=300`
  - `memory=1Gi`
- Runtime env contract:
  - `APP_ENV=staging|production`
  - `REQUIRED_PROVIDERS=openai,anthropic,google`
  - `LOG_LEVEL=INFO|DEBUG|WARNING`

## Smoke Tests

After deploy, the workflow requests an identity token and runs:

```bash
python scripts/smoke_runtime.py --base-url "$SERVICE_URL"
```

That sequence checks:

- `GET /healthz`
- `GET /readyz`
- `POST /execute` through `O-54`
- `POST /execute` through `C-OP46`
- `POST /execute` through `G-PRO`
