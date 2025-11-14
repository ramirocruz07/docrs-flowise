# High-Level Design (HLD)

## 1. Vision & Scope

Docr Canvas provides an interactive canvas-style UI where users can compose AI document-processing workflows. A Next.js frontend lets users drag/drop nodes, configure them, and submit documents. A FastAPI backend persists workflows, orchestrates execution, and integrates with LLM providers plus optional search APIs.

## 2. Target Users

- **Workflow authors**: Build reusable stacks of nodes for document QA.
- **Operators**: Run workflows in production, monitor execution, manage secrets.
- **Developers**: Extend the system with new node types or connectors.

## 3. Functional Overview

- Visual builder for workflows (CRUD stacks, nodes, and connections).
- Real-time configuration schema discovery per node type.
- Workflow execution endpoint accepting document uploads and returning answers.
- Optional persistence layer via SQLAlchemy-backed database.
- Pluggable node architecture (PDF loader, splitter, embeddings, vector store, QA, web search).

## 4. Architecture Summary

```
graph LR
    subgraph Client
        UI[Canvas Frontend<br/>Next.js/React]
    end

    subgraph Backend
        API[FastAPI Layer<br/>REST + WS]
        WF[Workflow Engine]
        Nodes[Node Library<br/>PDF/Text/LLM]
        DB[(SQL DB or SQLite)]
    end

    UI -->|HTTPS REST/WebSocket| API
    API --> WF
    WF --> Nodes
    API --> DB
    WF --> DB
```

## 5. Component Responsibilities

- **Canvas Frontend**
  - Renders draggable nodes & connections with React Flow.
  - Calls backend REST APIs (`/create-workflow`, `/add-node`, `/execute-workflow`, etc.).
  - Opens WebSocket for streaming updates (future live telemetry).
  - Uses `NEXT_PUBLIC_API_BASE_URL` env var for backend routing.

- **FastAPI Backend**
  - Loads environment secrets (`OPENAI_API_KEY`, `SERPAPI_KEY`, `BRAVE_API_KEY`).
  - Exposes CRUD endpoints for workflows and nodes plus execution endpoint accepting multipart form data.
  - Hosts WebSocket endpoint for interactive updates.
  - Initializes workflow state into in-memory cache and optional DB persistence.

- **Workflow Engine**
  - Maintains node graph, execution order, and connection metadata.
  - Performs topological sort and orchestrates async execution.
  - Injects node-specific inputs (documents, retrievers, prompts) from previous outputs.

- **Node Library**
  - Each node encapsulates domain-specific logic (PDF parsing, embeddings, vector store, QA chain, web search).
  - `process()` interface standardizes success/error payloads and declared inputs/outputs.

- **Persistence Layer**
  - SQLAlchemy models for workflows, nodes, and connections with SQLite defaults (files `docr.db`, `docrflowise.db`).
  - Optional migrations with Alembic.

## 6. Deployment Topology

- **Local/Dev**: Run both services directly or via provided Dockerfiles; metadata stored in SQLite.
- **Staging/Prod**:
  - Frontend served as Node app fronted by CDN/edge.
  - Backend runs behind API gateway with HTTPS termination.
  - Database may be upgraded to managed Postgres for multi-user persistence.
  - Secrets injected through container env vars or secret store.

```
flowchart LR
    CDN[(CDN / WAF)]
    FE[Frontend Container<br/>Next.js]
    API[Backend Container<br/>FastAPI]
    DB[(Managed PostgreSQL)]
    LLM[(OpenAI API)]
    Search[(SerpAPI / Brave)]

    CDN --> FE --> API
    API --> DB
    API -->|HTTPS| LLM
    API --> Search
```

## 7. Non-Functional Requirements

- **Security**: Secrets never baked into images; CORS limited to known origins.
- **Scalability**: Stateless FastAPI and Next.js containers can scale horizontally; workflows cached per instance.
- **Observability**: FastAPI logs execution order and node states; extendable to structured logging/metrics exporters.
- **Extensibility**: New node types simply implement `process()` and declare inputs/outputs.

## 8. Build & Release

- Dockerfiles at `backend/Dockerfile` and `docr-canvas-frontend/Dockerfile`.
- CI pipeline builds/pushes images, runs tests (unit + lint), and deploys to container registry.
- Environments configured via env files or secret managers.

