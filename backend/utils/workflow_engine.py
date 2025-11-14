from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import uuid

class NodeConnection(BaseModel):
    id: Optional[str] = None
    source_node: str
    source_output: str
    target_node: str
    target_input: str

class Workflow:
    def __init__(self, custom_prompt: Optional[str] = None):
        self.nodes: Dict[str, Any] = {}
        self.connections: List[NodeConnection] = []
        self.execution_order: List[str] = []
        self.custom_prompt: str = (custom_prompt or "").strip()
    
    def set_node_position(self, node_id: str, x: float, y: float):
        if node_id in self.nodes:
            self.nodes[node_id]['position'] = {
                'x': float(x),
                'y': float(y)
            }
        
    def add_node(self, node_id: str, node_instance: Any):
        self.nodes[node_id] = {
            'instance': node_instance,
            'data': {},
            'status': 'pending'
        }
        # Initialize position placeholder to avoid key errors
        self.set_node_position(node_id, 0.0, 0.0)
        
    def connect_nodes(self, connection: NodeConnection):
        self.connections.append(connection)
    
    def remove_node(self, node_id: str) -> bool:
        if node_id not in self.nodes:
            return False
        del self.nodes[node_id]
        self.connections = [
            conn for conn in self.connections
            if conn.source_node != node_id and conn.target_node != node_id
        ]
        if node_id in self.execution_order:
            self.execution_order = [nid for nid in self.execution_order if nid != node_id]
        return True
        
    def calculate_execution_order(self) -> List[str]:
        # Simple topological sort for execution order
        # This ensures nodes are executed after their dependencies
        visited = set()
        order = []
        
        def visit(node_id: str):
            if node_id in visited:
                return
            visited.add(node_id)
            
            # Find nodes that this node depends on
            for conn in self.connections:
                if conn.target_node == node_id:
                    visit(conn.source_node)
                    
            order.append(node_id)
        
        for node_id in self.nodes:
            visit(node_id)
            
        self.execution_order = order
        return order
    
    async def execute(self, initial_data: Dict[str, Any] = None) -> Dict[str, Any]:
        self.calculate_execution_order()
        results = initial_data or {}
        if self.custom_prompt:
            results.setdefault('custom_prompt', self.custom_prompt)
        
        print(f"Execution order: {self.execution_order}")
        print(f"Initial data keys: {list(results.keys())}")
        
        for node_id in self.execution_order:
            node_data = self.nodes[node_id]
            node = node_data['instance']
            
            try:
                print(f"\nExecuting node: {node_id} ({node.type})")
                
                # Prepare input data for this node
                input_data = {}
                
                # Add initial data (file_content, question) if node needs it
                if node.type == "pdf_loader" and 'file_content' in results:
                    input_data['file_content'] = results['file_content']
                elif node.type == "qa_chain" and 'question' in results:
                    input_data['question'] = results['question']
                    if 'custom_prompt' in results:
                        input_data['custom_prompt'] = results['custom_prompt']
                
                # Add data from connections
                for conn in self.connections:
                    if conn.target_node == node_id:
                        if conn.source_output in results:
                            input_data[conn.target_input] = results[conn.source_output]
                            print(f"  Connected input: {conn.target_input} = {conn.source_output} from {conn.source_node}")
                        else:
                            print(f"  WARNING: Source output '{conn.source_output}' not found in results")
                
                print(f"  Input data keys: {list(input_data.keys())}")
                print(f"  Node expects inputs: {node.inputs}")
                
                # Execute node
                if hasattr(node, 'process'):
                    if node.type == "pdf_loader":
                        file_content = input_data.get('file_content', results.get('file_content', b''))
                        result = await node.process(file_content)
                    elif node.type == "qa_chain":
                        # Initialize QA chain with retriever if available, or derive from vector_store if missing
                        retriever = input_data.get('retriever')
                        if not retriever and 'vector_store' in results:
                            try:
                                print("  Deriving retriever from vector_store...")
                                retriever = results['vector_store'].as_retriever()
                            except Exception:
                                retriever = None
                        if retriever and (not hasattr(node, 'qa_chain') or node.qa_chain is None):
                            print(f"  Initializing QA chain with retriever...")
                            node.initialize_chain(retriever)
                        result = node.process(
                            input_data.get('question', results.get('question', '')),
                            custom_prompt=input_data.get('custom_prompt', results.get('custom_prompt'))
                        )
                    elif node.type == "vector_store":
                        # Vector store needs documents (can be chunks from text splitter)
                        # It creates embeddings internally, so we don't need embeddings input
                        # Check both 'documents' and 'chunks' from input_data and results
                        documents = (input_data.get('documents') or 
                                    input_data.get('chunks') or
                                    results.get('documents') or
                                    results.get('chunks'))
                        if documents:
                            result = node.process(documents)
                        else:
                            raise ValueError(f"Vector Store needs 'documents' or 'chunks' input. Available: input_data={list(input_data.keys())}, results={list(results.keys())}")
                    elif node.type == "text_splitter":
                        # Text splitter expects 'documents' as a positional argument
                        documents = input_data.get('documents') or results.get('documents')
                        if documents:
                            result = node.process(documents)
                        else:
                            raise ValueError(f"Text Splitter needs 'documents' input. Available: input_data={list(input_data.keys())}, results={list(results.keys())}")
                    else:
                        # For other nodes, pass input_data as keyword arguments
                        # But only pass the keys that the node expects
                        filtered_input = {k: v for k, v in input_data.items() if k in node.inputs}
                        if filtered_input:
                            result = node.process(**filtered_input)
                        else:
                            raise ValueError(f"Node {node.type} needs inputs {node.inputs}, got: {list(input_data.keys())}")
                    
                    print(f"  Result success: {result.get('success', False)}")
                    if not result.get('success'):
                        print(f"  Result error: {result.get('error', 'Unknown error')}")
                        
                    # Store results
                    for output in node.outputs:
                        if output in result:
                            results[output] = result[output]
                            print(f"  Stored output: {output}")
                    
                    node_data['data'] = result
                    node_data['status'] = 'success' if result.get('success') else 'error'
                else:
                    raise AttributeError(f"Node {node.type} does not have a 'process' method")
                    
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"ERROR in node {node_id} ({node.type}): {str(e)}")
                print(f"Traceback: {error_trace}")
                node_data['status'] = 'error'
                node_data['data'] = {'error': str(e), 'traceback': error_trace}
                # Don't stop execution, continue with other nodes
                
        print(f"\nFinal results keys: {list(results.keys())}")
        return results