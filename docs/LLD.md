# Low-Level Design (LLD)

## 1. Module Breakdown

| Module | Location | Responsibilities | Key Dependencies |
| --- | --- | --- | --- |
| API Layer | `backend/app.py` | REST endpoints, input validation, CORS, WebSocket handling | FastAPI, Pydantic, SQLAlchemy |
| Workflow Engine | `backend/utils/workflow_engine.py` | Node graph management, topological ordering, execution orchestrator | Pydantic, asyncio |
| Node Implementations | `backend/nodes/*.py` | PDF ingestion, text splitting, embedding generation, vector stores, QA chain, web search | LangChain, OpenAI SDK, FAISS, SERP/Brave APIs |
| Persistence Layer | `backend/database.py` | SQLAlchemy models, session handling, CRUD | SQLAlchemy, Alembic |
| Frontend UI | `docr-canvas-frontend/app/*` | Canvas builder, config panels, API client, React Flow rendering | Next.js 16, React 19, React Flow |

## 2. Backend Detailed Flow

### 2.1 Workflow CRUD

```
sequenceDiagram
    participant UI as Canvas UI
    participant API as FastAPI
    participant DB as Database

    UI->>API: POST /create-workflow
    API->>DB: Insert new workflow row
    API-->>UI: workflow_id

    UI->>API: POST /add-node (workflow_id, node_type, config)
    API->>API: build_node_instance()
    API->>DB: Persist node (optional)
    API-->>UI: node metadata (inputs/outputs/position)

    UI->>API: POST /connect-nodes
    API->>DB: Persist connection (optional)
    API-->>UI: success
```

### 2.2 Execution Path

```
sequenceDiagram
    participant UI
    participant API as FastAPI /execute-workflow
    participant WF as Workflow Engine
    participant Nodes as Node Instances
    participant LLM as External APIs

    UI->>API: multipart form (workflow_id, question, file)
    API->>WF: ensure_workflow_loaded()
    API->>WF: workflow.execute(initial_data)
    loop Each node (topological order)
        WF->>Nodes: node.process(filtered_inputs)
        Nodes-->>WF: result dict (success flag, outputs)
        alt needs external data
            Nodes->>LLM: API call (OPENAI, SerpAPI, Brave)
            LLM-->>Nodes: response payload
        end
    end
    WF-->>API: aggregated results (answer, execution_order)
    API-->>UI: JSON response
```

### 2.3 Workflow Engine Data Structures

- `Workflow.nodes`: `{node_id: {"instance": Node, "data": dict, "status": str, "config": dict, "position": {x,y}}}`
- `Workflow.connections`: `List[NodeConnection]` describing directed edges.
- `NodeConnection`: `source_node`, `source_output`, `target_node`, `target_input`.
- `Workflow.execution_order`: list of node IDs produced by DFS-based topo sort.

## 3. Node Contracts

Every node exposes:

```python
class Node:
    type: str
    name: str
    inputs: List[str]
    outputs: List[str]

    async def process(...) -> Dict[str, Any]:
        return {
            "success": bool,
            "<output_name>": value,
            "error": Optional[str],
        }
```

- `PDFLoaderNode`: consumes `file_content` bytes, emits `documents`.
- `TextSplitterNode`: consumes `documents`, emits `chunks`.
- `EmbeddingsNode`: consumes `chunks`, emits `embeddings`.
- `VectorStoreNode`: consumes `documents`/`chunks`, emits `vector_store` and `retriever`.
- `QAChainNode`: consumes `question`, `retriever`, `custom_prompt`, emits `answer`.
- `WebSearchNode`: consumes `query`, emits `search_results`.

## 4. Database Schema (logical)

```
erDiagram
    Workflow ||--o{ Node : contains
    Workflow ||--o{ Connection : has
    Node ||--o{ Connection : source
    Node ||--o{ Connection : target

    Workflow {
      uuid id PK
      string name
      text description
      text custom_prompt
      datetime created_at
      datetime updated_at
    }
    Node {
      uuid id PK
      uuid workflow_id FK
      string node_type
      json config
      string position_x
      string position_y
    }
    Connection {
      uuid id PK
      uuid workflow_id FK
      uuid source_node_id FK
      uuid target_node_id FK
      string source_output
      string target_input
    }
```

- SQLite by default (files `docr.db`, `docrflowise.db`); upgradeable to Postgres by changing SQLAlchemy URL.

## 5. Frontend Architecture

```
graph TD
    App[Next.js App Router] --> Page[Canvas Page]
    Page --> Components(Canvas, Toolbar, ConfigPanel, ChatDialog)
    Components --> Hooks[React State / Context]
    Hooks --> APIClient[Axios Client]
    APIClient -->|REST/WebSocket| Backend[FastAPI]
```

- Uses React Flow for node graph interactions.
- Configuration forms adapt from schemas served by `/node-config-schema/{node_type}`.
- Chat dialog surfaces latest execution results via REST response or future WebSocket streaming.

## 6. Deployment Specifics

| Service | Image | Ports | Env |
| --- | --- | --- | --- |
| Backend | `backend/Dockerfile` | 8000 | `OPENAI_API_KEY`, `SERPAPI_KEY`, `BRAVE_API_KEY`, `DATABASE_URL`, etc. |
| Frontend | `docr-canvas-frontend/Dockerfile` | 3000 | `NEXT_PUBLIC_API_BASE_URL`, feature toggles |

- Use Docker network (e.g., `docr-net`) so frontend can reach backend by container name.
- Persistent storage: mount volume at `/app` if using SQLite; otherwise configure remote DB.

## 7. Extension Points

- **New Node Types**: Add module under `backend/nodes/`, expose config schema via `components/config_panel.py`, update UI to expose in palette.
- **Auth**: Introduce middleware on FastAPI to validate JWT/API keys.
- **Observability**: Instrument `Workflow.execute()` to push traces/metrics.

## 8. Risks & Mitigations

- **API Quotas**: Rate limit outbound calls and surface errors to UI.
- **Large PDFs**: Enforce max upload size via FastAPI settings; stream to disk if needed.
- **Inconsistent schemas**: Centralize config schema definitions and reuse in UI to avoid drift.


