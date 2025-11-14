'use client'
import React, { useCallback, useState } from 'react'
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
  Connection,
  NodeChange,
  EdgeChange,
} from 'reactflow'
import { Play } from 'lucide-react'
import axios from 'axios'
import { CanvasProps } from '@/types'
import { BackgroundVariant as ReactFlowBackgroundVariant } from 'reactflow'
import ConfigPanel from './ConfigPanel'

import 'reactflow/dist/style.css';

const Canvas: React.FC<CanvasProps> = ({ 
  workflowId, 
  nodes, 
  edges, 
  onNodesChange, 
  onEdgesChange,
  onRun
}) => {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [showConfigPanel, setShowConfigPanel] = useState<boolean>(false)

  const onNodesChangeHandler = useCallback(
    (changes: NodeChange[]) => {
      const updatedNodes = applyNodeChanges(changes, nodes)
      onNodesChange(updatedNodes)

      if (!workflowId) {
        return
      }

      const positionUpdates = changes.filter(
        (change) => change.type === 'position' && change.position && !change.dragging
      )

      positionUpdates.forEach((change) => {
        const updatedNode = updatedNodes.find((node) => node.id === change.id)
        if (!updatedNode) return

        axios.post(`http://localhost:8000/node/${workflowId}/${updatedNode.id}/position`, {
          x: updatedNode.position.x,
          y: updatedNode.position.y,
        }).catch((error) => {
          console.warn('Failed to update node position:', error)
        })
      })
    },
    [nodes, onNodesChange, workflowId]
  )

  const onEdgesChangeHandler = useCallback(
    (changes: EdgeChange[]) => {
      const updatedEdges = applyEdgeChanges(changes, edges)
      onEdgesChange(updatedEdges)
    },
    [edges, onEdgesChange]
  )

  const onConnect = useCallback(
    async (params: Connection) => {
      if (!workflowId) {
        console.error('Cannot connect nodes: No workflow ID')
        return
      }

      // Find source and target nodes
      const sourceNode = nodes.find(n => n.id === params.source)
      const targetNode = nodes.find(n => n.id === params.target)

      console.log('Connection attempt:', {
        source: params.source,
        target: params.target,
        sourceNode: sourceNode?.data,
        targetNode: targetNode?.data
      })

      if (!sourceNode || !targetNode) {
        console.error('Cannot connect: Source or target node not found')
        return
      }

      // Determine output and input based on node types
      // Map node types to their outputs/inputs
      const nodeTypeMap: Record<string, { outputs: string[], inputs: string[] }> = {
        'pdf_loader': { outputs: ['documents'], inputs: [] },
        'text_splitter': { outputs: ['chunks'], inputs: ['documents'] },
        'vector_store': { outputs: ['retriever', 'vector_store'], inputs: ['documents', 'chunks'] },
        'qa_chain': { outputs: ['answer'], inputs: ['retriever', 'question'] }
      }

      const sourceType = sourceNode.data.type
      const targetType = targetNode.data.type
      const sourceOutputs = nodeTypeMap[sourceType]?.outputs || []
      const targetInputs = nodeTypeMap[targetType]?.inputs || []

      // Validate connection direction
      if (sourceOutputs.length === 0) {
        alert(`❌ Invalid connection direction!\n\n${sourceNode.data.label} has no outputs.\n\nTip: Connect FROM nodes with outputs TO nodes with inputs.`)
        return
      }

      if (targetInputs.length === 0) {
        alert(`❌ Invalid connection direction!\n\n${targetNode.data.label} is a starting node with no inputs.\n\nTip: Connect FROM ${targetNode.data.label} TO other nodes, not the other way around.`)
        return
      }

      // Find matching output/input
      // Try to find a direct match first
      let sourceOutput = sourceOutputs.find(out => targetInputs.includes(out))
      let targetInput = targetInputs.find(inp => sourceOutputs.includes(inp))

      // If no direct match, use smart matching
      if (!sourceOutput || !targetInput) {
        // PDF Loader -> Text Splitter: documents -> documents
        if (sourceType === 'pdf_loader' && targetType === 'text_splitter') {
          sourceOutput = 'documents'
          targetInput = 'documents'
        }
        // Text Splitter -> Vector Store: chunks -> documents (chunks are documents)
        else if (sourceType === 'text_splitter' && targetType === 'vector_store') {
          sourceOutput = 'chunks'
          targetInput = 'documents'
        }
        // Vector Store -> QA Chain: retriever -> retriever
        else if (sourceType === 'vector_store' && targetType === 'qa_chain') {
          sourceOutput = 'retriever'
          targetInput = 'retriever'
        }
        // Default: use first available
        else {
          sourceOutput = sourceOutputs[0]
          targetInput = targetInputs[0]
        }
      }

      // Validate we have valid values
      if (!sourceOutput || !targetInput) {
        console.error('Invalid connection mapping:', { sourceType, targetType, sourceOutput, targetInput })
        alert(`Cannot determine connection mapping between ${sourceNode.data.label} and ${targetNode.data.label}`)
        return
      }

      try {
        console.log('Connecting nodes:', {
          workflow_id: workflowId,
          source_node: params.source,
          source_output: sourceOutput,
          target_node: params.target,
          target_input: targetInput
        })

        // Send connection to backend
        const response = await axios.post('http://localhost:8000/connect-nodes', {
          workflow_id: workflowId,
          source_node: params.source,
          source_output: sourceOutput,
          target_node: params.target,
          target_input: targetInput
        })

        console.log('Connection successful:', response.data)

        // Update frontend edges
        const newEdge = addEdge(params, edges)
        onEdgesChange(newEdge)
      } catch (error) {
        console.error('Failed to connect nodes:', error)
        
        let errorMessage = 'Failed to connect nodes'
        if (axios.isAxiosError(error)) {
          if (error.response?.data?.detail) {
            errorMessage = error.response.data.detail
          } else if (error.response?.status === 422) {
            errorMessage = 'Invalid connection: Please check that the nodes are compatible'
          }
        }
        
        alert(`Error: ${errorMessage}`)
      }
    },
    [edges, onEdgesChange, nodes, workflowId],
  )

  const handleNodeDeleted = useCallback((deletedNodeId: string) => {
    onNodesChange((prevNodes) =>
      prevNodes.filter((node) => node.id !== deletedNodeId)
    )
    onEdgesChange((prevEdges) =>
      prevEdges.filter(
        (edge) => edge.source !== deletedNodeId && edge.target !== deletedNodeId
      )
    )
    setShowConfigPanel(false)
    setSelectedNodeId(null)
  }, [onEdgesChange, onNodesChange])


  return (
    <div className="flex-1 flex">
      {/* React Flow Canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChangeHandler}
          onEdgesChange={onEdgesChangeHandler}
          onConnect={onConnect}
          onNodeClick={(event, node) => {
            setSelectedNodeId(node.id)
            setShowConfigPanel(true)
          }}
          fitView
          nodesDraggable={true}
        >
          <Controls />
          <MiniMap />
          <Background variant={ReactFlowBackgroundVariant.Dots} gap={12} size={1} />
        </ReactFlow>
      </div>

      {/* Execution Panel */}
      <div className="w-80 bg-white border-l border-gray-200 p-4 flex flex-col">
        <h3 className="text-lg font-semibold mb-4">Run Pipeline</h3>
        
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-4">
            Click the button below to open the chat interface and test your stack.
          </p>
        </div>

        {/* Run Button */}
        <button
          onClick={() => onRun?.()}
          disabled={!workflowId || nodes.length === 0}
          className="w-full bg-green-500 text-white py-3 px-4 rounded-lg hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center justify-center mb-4 font-semibold"
        >
          <Play size={20} className="mr-2" />
          Run Stack
        </button>

        <div className="mt-auto pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            Build your workflow by adding nodes from the sidebar and connecting them.
          </p>
        </div>
      </div>

      {/* Configuration Panel */}
      {showConfigPanel && selectedNodeId && (
        <ConfigPanel
          nodeId={selectedNodeId}
          nodeType={nodes.find(n => n.id === selectedNodeId)?.data.type || null}
          workflowId={workflowId}
          onClose={() => {
            setShowConfigPanel(false)
            setSelectedNodeId(null)
          }}
          onConfigUpdate={() => {
            // Refresh nodes or update UI as needed
            console.log('Configuration updated')
          }}
          onNodeDelete={handleNodeDeleted}
        />
      )}
    </div>
  )
}

export default Canvas