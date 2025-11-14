## Docker Images

This repository now ships with Dockerfiles for the FastAPI backend (`backend/Dockerfile`) and the Next.js frontend (`docr-canvas-frontend/Dockerfile`). Use this guide to build and run container images locally or in CI.

### Prerequisites

- Docker 24+ (or any recent version that supports multi-stage builds)
- Access to any required API keys (`OPENAI_API_KEY`, `SERPAPI_KEY`, `BRAVE_API_KEY`, etc.)
- Optional: a `.env`/`wow.env` file for the backend and `NEXT_PUBLIC_*` env vars for the frontend

### 1. Backend Image

```
docker build -t docr-backend ./backend
```

Runtime example (loads env vars from an existing file and exposes port 8000):

```
docker run \
  --rm \
  --name docr-backend \
  --env-file backend/wow.env \
  -p 8000:8000 \
  docr-backend
```

> If you rely on the bundled SQLite databases (`docr.db`, `docrflowise.db`), mount a docker volume (`-v docr-data:/app`) so data persists across container restarts.

### 2. Frontend Image

```
docker build -t docr-frontend ./docr-canvas-frontend
```

Runtime example (point the UI at the backend API and expose port 3000):

```
docker run \
  --rm \
  --name docr-frontend \
  -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 \
  -p 3000:3000 \
  docr-frontend
```

### Networking Tips

- When running both containers locally, create a user-defined bridge network so services can reach each other by name:
  ```
  docker network create docr-net
  docker run -d --network docr-net --name docr-backend docr-backend
  docker run -d --network docr-net --name docr-frontend \
    -e NEXT_PUBLIC_API_BASE_URL=http://docr-backend:8000 \
    -p 3000:3000 \
    docr-frontend
  ```
- In production orchestrators (Compose, Kubernetes, etc.) pass the same environment variables shown above.

### Image Update Checklist

1. Backend dependencies live in `backend/requirements.txt`. Rebuild whenever the file changes.
2. Frontend uses `npm ci`; an updated `package-lock.json` will trigger new modules.
3. All env files are _not_ baked into images—mount them at runtime for security.


