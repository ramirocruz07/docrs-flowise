from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import json
import uuid
import os
import pathlib
from dotenv import load_dotenv

from utils.workflow_engine import Workflow, NodeConnection
from nodes.pdf_loader import PDFLoaderNode
from nodes.text_splitter import TextSplitterNode
from nodes.embeddings import EmbeddingsNode
from nodes.vector_store import VectorStoreNode
from nodes.qa_chain import QAChainNode
from nodes.web_search import WebSearchNode
try:
    from database import init_db, get_db, WorkflowModel, NodeModel, ConnectionModel
    from components.config_panel import NodeConfigSchema
    from sqlalchemy.orm import Session
    DB_ENABLED = True
except ImportError:
    DB_ENABLED = False
    print("Warning: Database modules not available. Running without persistence.")

# Load environment variables
# Try to load from wow.env first, then .env
# Get the directory where this file is located
backend_dir = pathlib.Path(__file__).parent
wow_env_path = str(backend_dir / "wow.env")
env_path = str(backend_dir / ".env")

# Load environment files (try multiple locations)
wow_loaded = False
env_loaded = False

# Try loading from backend directory
if pathlib.Path(wow_env_path).exists():
    wow_loaded = load_dotenv(wow_env_path)
if pathlib.Path(env_path).exists():
    env_loaded = load_dotenv(env_path, override=True)

# Fallback: try loading from current directory (in case server runs from different location)
if not wow_loaded:
    wow_loaded = load_dotenv("wow.env")
if not env_loaded:
    env_loaded = load_dotenv(".env", override=True)

# Verify API key is loaded (for debugging)
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("=" * 60)
    print("WARNING: OPENAI_API_KEY not found in environment variables!")
    print(f"Backend directory: {backend_dir}")
    print(f"wow.env path: {wow_env_path}")
    print(f"wow.env exists: {pathlib.Path(wow_env_path).exists()}")
    print(f"wow.env loaded: {wow_loaded}")
    print(f".env path: {env_path}")
    print(f".env exists: {pathlib.Path(env_path).exists()}")
    print(f".env loaded: {env_loaded}")
    print("=" * 60)
else:
    print(f"✓ OPENAI_API_KEY loaded successfully (length: {len(api_key)})")
    print(f"  Source: {'wow.env' if wow_loaded else ('.env' if env_loaded else 'environment')}")

app = FastAPI(title="Docr Canvas API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active workflows (in-memory cache)
active_workflows: Dict[str, Workflow] = {}

# Initialize database if available
if DB_ENABLED:
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"Warning: Database initialization failed: {e}")
        DB_ENABLED = False

class CreateWorkflowRequest(BaseModel):
    name: str
    description: Optional[str] = None
    custom_prompt: Optional[str] = None

class AddNodeRequest(BaseModel):
    workflow_id: str
    node_type: str
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Optional[Dict[str, float]] = None

class ConnectNodesRequest(BaseModel):
    workflow_id: str
    source_node: str
    source_output: str
    target_node: str
    target_input: str

class ExecuteWorkflowRequest(BaseModel):
    workflow_id: str
    question: str

class UpdateNodePositionRequest(BaseModel):
    x: float
    y: float

def _safe_float(value: Any) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def _json_sanitise(value: Any, *, max_depth: int = 5) -> Any:
    """Recursively trim complex objects into JSON-safe primitives."""
    if max_depth <= 0:
        return None
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        sanitized_dict = {}
        for k, v in value.items():
            sanitized_value = _json_sanitise(v, max_depth=max_depth - 1)
            if sanitized_value is not None:
                sanitized_dict[k] = sanitized_value
        return sanitized_dict
    if isinstance(value, (list, tuple, set)):
        sanitized_list = []
        for item in value:
            sanitized_value = _json_sanitise(item, max_depth=max_depth - 1)
            if sanitized_value is not None:
                sanitized_list.append(sanitized_value)
        return sanitized_list
    # Unsupported types -> None (omit)
    return None

def build_node_instance(node_type: str, config: Optional[Dict[str, Any]] = None):
    cfg = config or {}
    if node_type == "pdf_loader":
        return PDFLoaderNode()
    elif node_type == "text_splitter":
        node_config = TextSplitterNode.Config(**cfg)
        return TextSplitterNode(node_config)
    elif node_type == "embeddings":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY environment variable is not set. Please set it in your .env file."
            )
        node_config = EmbeddingsNode.Config(**cfg)
        return EmbeddingsNode(node_config, api_key=api_key)
    elif node_type == "vector_store":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY environment variable is not set. Please set it in your .env file."
            )
        node_config = VectorStoreNode.Config(**cfg)
        return VectorStoreNode(node_config, api_key=api_key)
    elif node_type == "qa_chain":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY environment variable is not set. Please set it in your .env file."
            )
        node_config = QAChainNode.Config(**cfg)
        return QAChainNode(node_config, api_key=api_key)
    elif node_type == "web_search":
        node_config = WebSearchNode.Config(**cfg)
        provider = node_config.provider if hasattr(node_config, "provider") else cfg.get("provider", "serpapi")
        if provider == "brave":
            brave_key = os.getenv("BRAVE_API_KEY")
            if not brave_key:
                raise HTTPException(
                    status_code=400,
                    detail="BRAVE_API_KEY environment variable is not set. Please set it in your .env file."
                )
            return WebSearchNode(node_config, serpapi_key=None, brave_key=brave_key)
        else:
            serpapi_key = os.getenv("SERPAPI_KEY")
            if not serpapi_key:
                raise HTTPException(
                    status_code=400,
                    detail="SERPAPI_KEY environment variable is not set. Please set it in your .env file."
                )
            return WebSearchNode(node_config, serpapi_key=serpapi_key, brave_key=None)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown node type: {node_type}")

def ensure_workflow_loaded(workflow_id: str) -> Workflow:
    if workflow_id in active_workflows:
        return active_workflows[workflow_id]
    
    if not DB_ENABLED:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    db = next(get_db())
    try:
        workflow_model = db.query(WorkflowModel).filter(WorkflowModel.id == workflow_id).first()
        if not workflow_model:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = Workflow(custom_prompt=workflow_model.custom_prompt)
        active_workflows[workflow_id] = workflow
        
        node_models = db.query(NodeModel).filter(NodeModel.workflow_id == workflow_id).all()
        for node_model in node_models:
            node_instance = build_node_instance(node_model.node_type, node_model.config or {})
            workflow.add_node(node_model.id, node_instance)
            workflow.nodes[node_model.id]['config'] = node_model.config or {}
            workflow.set_node_position(
                node_model.id,
                _safe_float(node_model.position_x),
                _safe_float(node_model.position_y)
            )
        
        connection_models = db.query(ConnectionModel).filter(ConnectionModel.workflow_id == workflow_id).all()
        for conn_model in connection_models:
            connection = NodeConnection(
                id=conn_model.id,
                source_node=conn_model.source_node_id,
                source_output=conn_model.source_output,
                target_node=conn_model.target_node_id,
                target_input=conn_model.target_input
            )
            workflow.connect_nodes(connection)
        
        return workflow
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Docr Canvas API", "status": "running"}

@app.get("/stacks")
async def list_stacks():
    """List all stacks/workflows"""
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            workflows = db.query(WorkflowModel).order_by(WorkflowModel.created_at.desc()).all()
            return {
                "stacks": [
                    {
                        "id": w.id,
                        "name": w.name,
                        "description": w.description or "",
                        "custom_prompt": w.custom_prompt or "",
                        "created_at": w.created_at.isoformat() if w.created_at else None,
                        "updated_at": w.updated_at.isoformat() if w.updated_at else None
                    }
                    for w in workflows
                ]
            }
        except Exception as e:
            print(f"Error listing stacks: {e}")
            return {"stacks": []}
        finally:
            if db:
                db.close()
    else:
        # Return in-memory workflows
        return {
            "stacks": [
                {
                    "id": workflow_id,
                    "name": f"Workflow {workflow_id[:8]}",
                    "description": "",
                    "custom_prompt": workflow.custom_prompt if hasattr(workflow, "custom_prompt") else "",
                    "created_at": None,
                    "updated_at": None
                }
                for workflow_id, workflow in active_workflows.items()
            ]
        }

@app.get("/stack/{stack_id}")
async def get_stack(stack_id: str):
    """Get a specific stack by ID"""
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            workflow = db.query(WorkflowModel).filter(WorkflowModel.id == stack_id).first()
            if not workflow:
                raise HTTPException(status_code=404, detail="Stack not found")
            
            ensure_workflow_loaded(stack_id)
            
            return {
                "id": workflow.id,
                "name": workflow.name,
                "description": workflow.description or "",
                "custom_prompt": workflow.custom_prompt or "",
                "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
                "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None
            }
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error getting stack: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if db:
                db.close()
    else:
        if stack_id not in active_workflows:
            raise HTTPException(status_code=404, detail="Stack not found")
        return {
            "id": stack_id,
            "name": f"Workflow {stack_id[:8]}",
            "description": "",
            "custom_prompt": active_workflows[stack_id].custom_prompt if hasattr(active_workflows[stack_id], "custom_prompt") else "",
            "created_at": None,
            "updated_at": None
        }

@app.delete("/stack/{stack_id}")
async def delete_stack(stack_id: str):
    """Delete a stack"""
    if stack_id in active_workflows:
        del active_workflows[stack_id]
    
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            workflow = db.query(WorkflowModel).filter(WorkflowModel.id == stack_id).first()
            if workflow:
                db.delete(workflow)
                db.commit()
            return {"message": "Stack deleted successfully"}
        except Exception as e:
            print(f"Error deleting stack: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if db:
                db.close()
    
    return {"message": "Stack deleted successfully"}

@app.post("/create-workflow")
async def create_workflow(request: CreateWorkflowRequest):
    workflow_id = str(uuid.uuid4())
    workflow = Workflow(custom_prompt=request.custom_prompt)
    active_workflows[workflow_id] = workflow
    
    # Persist to database if enabled
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            db_workflow = WorkflowModel(
                id=workflow_id,
                name=request.name,
                description=request.description,
                custom_prompt=(request.custom_prompt or "").strip()
            )
            db.add(db_workflow)
            db.commit()
            print(f"✓ Workflow {workflow_id} saved to database")
        except Exception as e:
            print(f"Warning: Failed to save workflow to database: {e}")
        finally:
            if db:
                db.close()
    
    return {
        "workflow_id": workflow_id,
        "name": request.name,
        "custom_prompt": (request.custom_prompt or "").strip(),
        "message": "Workflow created successfully"
    }

@app.post("/add-node")
async def add_node(request: AddNodeRequest):
    if request.workflow_id not in active_workflows:
        ensure_workflow_loaded(request.workflow_id)
    if request.workflow_id not in active_workflows:
        ensure_workflow_loaded(request.workflow_id)
    if request.workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[request.workflow_id]
    node_id = str(uuid.uuid4())
    
    try:
        node = build_node_instance(request.node_type, request.config)
        workflow.add_node(node_id, node)
        workflow.nodes[node_id]['config'] = request.config or {}
        position_payload = request.position or {}
        workflow.set_node_position(
            node_id,
            position_payload.get('x', 0.0),
            position_payload.get('y', 0.0)
        )
        
        # Persist to database if enabled
        if DB_ENABLED:
            db = None
            try:
                db = next(get_db())
                db_node = NodeModel(
                    id=node_id,
                    workflow_id=request.workflow_id,
                    node_type=request.node_type,
                    config=request.config or {},
                    position_x=str(position_payload.get('x', 0.0)),
                    position_y=str(position_payload.get('y', 0.0))
                )
                db.add(db_node)
                db.commit()
                print(f"✓ Node {node_id} saved to database")
            except Exception as e:
                print(f"Warning: Failed to save node to database: {e}")
            finally:
                if db:
                    db.close()
        
        return {
            "node_id": node_id,
            "node_type": request.node_type,
            "inputs": node.inputs,
            "outputs": node.outputs,
            "position": workflow.nodes[node_id].get('position', {'x': 0.0, 'y': 0.0})
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to create node: {str(e)}"
        )

@app.post("/connect-nodes")
async def connect_nodes(request: ConnectNodesRequest):
    if request.workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[request.workflow_id]
    connection_id = str(uuid.uuid4())
    connection = NodeConnection(
        id=connection_id,
        source_node=request.source_node,
        source_output=request.source_output,
        target_node=request.target_node,
        target_input=request.target_input
    )
    
    workflow.connect_nodes(connection)
    
    # Persist to database if enabled
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            db_conn = ConnectionModel(
                id=connection_id,
                workflow_id=request.workflow_id,
                source_node_id=request.source_node,
                target_node_id=request.target_node,
                source_output=request.source_output,
                target_input=request.target_input
            )
            db.add(db_conn)
            db.commit()
            print(f"✓ Connection {connection_id} saved to database")
        except Exception as e:
            print(f"Warning: Failed to save connection to database: {e}")
        finally:
            if db:
                db.close()
    
    return {"message": "Nodes connected successfully"}

@app.post("/execute-workflow")
async def execute_workflow(
    workflow_id: str = Form(...),
    question: str = Form(...),
    file: UploadFile = File(...)
):
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Prepare initial data
        initial_data = {
            'file_content': file_content,
            'question': question,
            'custom_prompt': workflow.custom_prompt if hasattr(workflow, "custom_prompt") else ""
        }
        
        # Execute workflow
        results = await workflow.execute(initial_data)
        
        # Check if execution was successful
        if 'answer' in results:
            return {
                "success": True,
                "results": {
                    "answer": results.get('answer', 'No answer generated')
                },
                "execution_order": workflow.execution_order
            }
        else:
            # Check for errors in node execution
            error_messages = []
            for node_id, node_data in workflow.nodes.items():
                if node_data.get('status') == 'error':
                    error_info = node_data.get('data', {})
                    error_msg = error_info.get('error', 'Unknown error')
                    node_instance = node_data.get('instance')
                    node_name = node_instance.name if node_instance and hasattr(node_instance, 'name') else node_id
                    error_messages.append(f"{node_name}: {error_msg}")
            
            if error_messages:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Workflow execution failed: {'; '.join(error_messages)}"
                )
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="Workflow execution failed: No answer generated. Check node connections and execution order."
                )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Workflow execution error: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")

@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    
    nodes_payload = []
    for node_id, data in workflow.nodes.items():
        instance = data['instance']
        node_entry = {
            "id": node_id,
            "type": getattr(instance, "type", None),
            "name": getattr(instance, "name", None),
            "inputs": getattr(instance, "inputs", []),
            "outputs": getattr(instance, "outputs", []),
            "status": data.get('status'),
            "config": data.get('config', {}),
            "position": data.get('position', {'x': 0.0, 'y': 0.0})
        }
        sanitized_data = _json_sanitise(data.get('data'))
        if sanitized_data:
            node_entry["data"] = sanitized_data
        nodes_payload.append(node_entry)
    
    connections_payload = []
    for conn in workflow.connections:
        connections_payload.append({
            "id": getattr(conn, "id", None),
            "source_node": conn.source_node,
            "source_output": conn.source_output,
            "target_node": conn.target_node,
            "target_input": conn.target_input
        })
    
    return {
        "workflow_id": workflow_id,
        "custom_prompt": workflow.custom_prompt,
        "nodes": nodes_payload,
        "connections": connections_payload
    }

@app.get("/node-config-schema/{node_type}")
async def get_node_config_schema(node_type: str):
    """Get configuration schema for a node type"""
    try:
        schema = NodeConfigSchema.get_schema(node_type)
        return {"fields": schema.get("fields", [])}
    except Exception as e:
        # Fallback if config panel module not available
        return {"fields": []}

@app.get("/node/{workflow_id}/{node_id}/config")
async def get_node_config(workflow_id: str, node_id: str):
    """Get current configuration for a node"""
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    if node_id not in workflow.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    node_data = workflow.nodes[node_id]
    node_instance = node_data['instance']
    
    # Get config from node instance
    config = {}
    if hasattr(node_instance, 'config'):
        if hasattr(node_instance.config, 'dict'):
            config = node_instance.config.dict()
        elif isinstance(node_instance.config, dict):
            config = node_instance.config
        else:
            config = vars(node_instance.config) if hasattr(node_instance.config, '__dict__') else {}
    
    return {"config": config}

@app.post("/node/{workflow_id}/{node_id}/config")
async def update_node_config(workflow_id: str, node_id: str, request: Dict[str, Any]):
    """Update configuration for a node"""
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    if node_id not in workflow.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    config = request.get("config", {})
    node_data = workflow.nodes[node_id]
    node_instance = node_data['instance']
    
    # Store config in node data
    node_data['config'] = config
    
    # If DB is enabled, persist to database
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            db_node = db.query(NodeModel).filter(
                NodeModel.id == node_id,
                NodeModel.workflow_id == workflow_id
            ).first()
            if db_node:
                db_node.config = config
                db.commit()
        except Exception as e:
            print(f"Failed to persist config to database: {e}")
        finally:
            if db:
                db.close()
    
    return {"message": "Configuration updated successfully", "config": config}

@app.post("/node/{workflow_id}/{node_id}/position")
async def update_node_position(workflow_id: str, node_id: str, request: UpdateNodePositionRequest):
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    if node_id not in workflow.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    workflow.set_node_position(node_id, request.x, request.y)
    
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            db_node = db.query(NodeModel).filter(
                NodeModel.id == node_id,
                NodeModel.workflow_id == workflow_id
            ).first()
            if db_node:
                db_node.position_x = str(request.x)
                db_node.position_y = str(request.y)
                db.commit()
        except Exception as e:
            print(f"Failed to persist node position to database: {e}")
        finally:
            if db:
                db.close()
    
    return {"message": "Position updated successfully"}

@app.delete("/node/{workflow_id}/{node_id}")
async def delete_node(workflow_id: str, node_id: str):
    if workflow_id not in active_workflows:
        ensure_workflow_loaded(workflow_id)
    if workflow_id not in active_workflows:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow = active_workflows[workflow_id]
    if node_id not in workflow.nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    workflow.remove_node(node_id)
    
    if DB_ENABLED:
        db = None
        try:
            db = next(get_db())
            db.query(ConnectionModel).filter(
                ConnectionModel.workflow_id == workflow_id,
                (ConnectionModel.source_node_id == node_id) | (ConnectionModel.target_node_id == node_id)
            ).delete(synchronize_session=False)
            db_node = db.query(NodeModel).filter(
                NodeModel.id == node_id,
                NodeModel.workflow_id == workflow_id
            ).first()
            if db_node:
                db.delete(db_node)
            db.commit()
        except Exception as e:
            print(f"Failed to delete node from database: {e}")
            raise HTTPException(status_code=500, detail="Failed to delete node from database")
        finally:
            if db:
                db.close()
    
    return {"message": "Node deleted successfully"}

@app.websocket("/ws/{workflow_id}")
async def websocket_endpoint(websocket: WebSocket, workflow_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Handle real-time updates
            await websocket.send_text(json.dumps({"type": "update", "data": "Processing..."}))
    except WebSocketDisconnect:
        print("Client disconnected")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )