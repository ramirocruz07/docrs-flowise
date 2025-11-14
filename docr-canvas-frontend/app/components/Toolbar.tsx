'use client'
import { useState } from 'react'
import {
  FileText,
  Scissors,
  Layers,
  Database,
  MessageCircle,
  Play,
  Search,
} from 'lucide-react'
import axios from 'axios'
import { ToolbarProps, NodeType, WorkflowNode } from '@/types'

const NODE_TYPES: NodeType[] = [
  {
    type: 'pdf_loader',
    name: 'PDF Loader',
    icon: FileText,
    description: 'Load and extract text from PDF files',
    inputs: [],
    outputs: ['documents']
  },
  {
    type: 'text_splitter',
    name: 'Text Splitter',
    icon: Scissors,
    description: 'Split text into chunks for processing',
    inputs: ['documents'],
    outputs: ['chunks']
  },
  {
    type: 'embeddings',
    name: 'Embeddings',
    icon: Layers,
    description: 'Convert text to vector embeddings',
    inputs: ['text'],
    outputs: ['embeddings']
  },
  {
    type: 'vector_store',
    name: 'Vector Store',
    icon: Database,
    description: 'Store and search vector embeddings',
    inputs: ['documents', 'embeddings'],
    outputs: ['vector_store', 'retriever']
  },
  {
    type: 'qa_chain',
    name: 'QA Chain',
    icon: MessageCircle,
    description: 'Answer questions based on retrieved context',
    inputs: ['retriever', 'question'],
    outputs: ['answer']
  },
  {
    type: 'web_search',
    name: 'Web Search',
    icon: Search,
    description: 'Search the web for information',
    inputs: ['query'],
    outputs: ['search_results']
  }
]

const Toolbar: React.FC<ToolbarProps> = ({
  workflowId,
  setWorkflowId,
  onNodesChange,
}) => {
  const [isCreating, setIsCreating] = useState<boolean>(false)

  const createWorkflow = async (e: React.MouseEvent<HTMLButtonElement>): Promise<void> => {
    e.preventDefault()
    e.stopPropagation()
    
    if (isCreating) return
    
    setIsCreating(true)
    try {
      const response = await axios.post(
        'http://localhost:8000/create-workflow',
        {
          name: 'New RAG Pipeline'
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 5000,
        }
      )
      setWorkflowId(response.data.workflow_id)
    } catch (error: unknown) {
      console.error('Failed to create workflow:', error)
      
      let errorMessage = 'Failed to create workflow'
      if (axios.isAxiosError(error)) {
        if (error.code === 'ECONNREFUSED' || error.message.includes('Network Error') || error.code === 'ERR_NETWORK') {
          errorMessage = '❌ Cannot connect to backend server!\n\nPlease make sure:\n1. Backend server is running\n2. Run: cd backend && python -m uvicorn app:app --reload\n3. Server should be on http://localhost:8000'
        } else if (error.response?.data?.detail) {
          errorMessage = error.response.data.detail
        } else if (error.response?.status) {
          errorMessage = `Server error: ${error.response.status} - ${error.response.statusText}`
        } else if (error.message) {
          errorMessage = error.message
        } else {
          errorMessage = 'Network error occurred. Check if backend server is running.'
        }
      } else if (error instanceof Error) {
        errorMessage = error.message
      }
      
      alert(`Error: ${errorMessage}`)
    } finally {
      setIsCreating(false)
    }
  }

  const addNodeToCanvas = async (nodeType: string): Promise<void> => {
    if (!workflowId) {
      alert('Please create a workflow first')
      return
    }

    try {
      const initialPosition = {
        x: Math.random() * 400,
        y: Math.random() * 400,
      }

      const response = await axios.post('http://localhost:8000/add-node', {
        workflow_id: workflowId,
        node_type: nodeType,
        config: {},
        position: initialPosition,
      })

      const responsePosition = response.data.position || {}
      const posX = Number(responsePosition.x ?? initialPosition.x)
      const posY = Number(responsePosition.y ?? initialPosition.y)
      const normalizedPosition = {
        x: Number.isFinite(posX) ? posX : initialPosition.x,
        y: Number.isFinite(posY) ? posY : initialPosition.y,
      }

      const newNode: WorkflowNode = {
        id: response.data.node_id,
        type: 'default',
        position: normalizedPosition,
        data: { 
          label: NODE_TYPES.find(n => n.type === nodeType)?.name || nodeType,
          type: nodeType
        }
      }

      onNodesChange((nds: WorkflowNode[]) => [...nds, newNode])

      try {
        await axios.post(`http://localhost:8000/node/${workflowId}/${response.data.node_id}/position`, {
          x: newNode.position.x,
          y: newNode.position.y,
        })
      } catch (error) {
        console.warn('Failed to persist node position:', error)
      }
    } catch (error: unknown) {
      console.error('Failed to add node:', error)
      
      let errorMessage = 'Failed to add node to workflow'
      if (axios.isAxiosError(error) && error.response?.data?.detail) {
        errorMessage = error.response.data.detail
      } else if (error instanceof Error) {
        errorMessage = error.message
      }
      
      alert(`Error: ${errorMessage}`)
    }
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 p-4">
      <div className="mb-6">
        <h3 className="text-lg font-semibold mb-3">RAG Pipeline Builder</h3>
        
        {!workflowId ? (
          <button
            type="button"
            onClick={createWorkflow}
            disabled={isCreating}
            className="w-full bg-green-500 text-white py-2 px-4 rounded-lg hover:bg-green-600 disabled:bg-gray-400 flex items-center justify-center"
          >
            {isCreating ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            ) : (
              <>
                <Play size={16} className="mr-2" />
                Create New Workflow
              </>
            )}
          </button>
        ) : (
          <div className="text-sm text-green-600 bg-green-50 p-2 rounded">
            ✓ Workflow Active
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h4 className="font-medium text-gray-700">Add Nodes</h4>
        {NODE_TYPES.map((node: NodeType) => (
          <button
            key={node.type}
            type="button"
            onClick={() => addNodeToCanvas(node.type)}
            disabled={!workflowId}
            className="w-full text-left p-3 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed flex items-start space-x-3"
          >
            <node.icon size={18} className="text-blue-500 mt-0.5 shrink-0" />
            <div>
              <div className="font-medium text-sm">{node.name}</div>
              <div className="text-xs text-gray-500">{node.description}</div>
            </div>
          </button>
        ))}
      </div>

      <div className="mt-6 pt-4 border-t border-gray-200">
        <h4 className="font-medium text-gray-700 mb-2">How to Build</h4>
        <ol className="text-sm text-gray-600 space-y-2">
          <li>1. Create a workflow</li>
          <li>2. Add nodes from left to right</li>
          <li>3. Connect nodes by dragging</li>
          <li>4. Upload PDF and ask questions</li>
        </ol>
      </div>
    </div>
  )
}

export default Toolbar