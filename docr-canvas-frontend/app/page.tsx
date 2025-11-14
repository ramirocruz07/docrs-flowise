'use client'
import { useEffect, useState } from 'react'
import Canvas from './components/canvas'
import Toolbar from './components/Toolbar'
import StacksView from './components/StacksView'
import ChatDialog from './components/ChatDialog'
import type { WorkflowEdge, WorkflowNode } from '@/types'
import axios from 'axios'

export default function Home() {
  const [currentView, setCurrentView] = useState<'stacks' | 'canvas'>('stacks')
  const [workflowId, setWorkflowId] = useState<string | null>(null)
  const [nodes, setNodes] = useState<WorkflowNode[]>([])
  const [edges, setEdges] = useState<WorkflowEdge[]>([])
  const [showChatDialog, setShowChatDialog] = useState(false)
  const [pendingChatWorkflowId, setPendingChatWorkflowId] = useState<string | null>(null)

  const handleSelectStack = (stackId: string) => {
    setPendingChatWorkflowId(null)
    setWorkflowId(stackId)
    setCurrentView('canvas')
  }

  const handleOpenStackChat = (stackId: string) => {
    setPendingChatWorkflowId(stackId)
    setWorkflowId(stackId)
    setCurrentView('canvas')
  }

  const handleBackToStacks = () => {
    setCurrentView('stacks')
    setWorkflowId(null)
    setNodes([])
    setEdges([])
    setShowChatDialog(false)
    setPendingChatWorkflowId(null)
  }

  useEffect(() => {
    const fetchWorkflow = async () => {
      if (!workflowId) {
        setNodes([])
        setEdges([])
        return
      }

      try {
        const response = await axios.get(`http://localhost:8000/workflow/${workflowId}`)
        const data = response.data

        const loadedNodes: WorkflowNode[] = (data.nodes || []).map((node: any) => {
          const rawX = Number(node.position?.x ?? 0)
          const rawY = Number(node.position?.y ?? 0)
          const position = {
            x: Number.isFinite(rawX) ? rawX : 0,
            y: Number.isFinite(rawY) ? rawY : 0,
          }

          return {
            id: node.id,
            type: 'default',
            position,
            data: {
              label: node.name || node.type || 'Node',
              type: node.type || 'unknown',
            },
          }
        })

        const loadedEdges: WorkflowEdge[] = (data.connections || []).map((conn: any, index: number) => ({
          id: conn.id || `${conn.source_node}-${conn.target_node}-${index}`,
          source: conn.source_node,
          target: conn.target_node,
          sourceHandle: conn.source_output,
          targetHandle: conn.target_input,
          label: conn.source_output === conn.target_input ? conn.source_output : `${conn.source_output}→${conn.target_input}`,
        }))

        setNodes(loadedNodes)
        setEdges(loadedEdges)

        if (pendingChatWorkflowId && pendingChatWorkflowId === workflowId) {
          setShowChatDialog(true)
          setPendingChatWorkflowId(null)
        }
      } catch (error) {
        console.error('Failed to load workflow:', error)
        setNodes([])
        setEdges([])
        setPendingChatWorkflowId(null)
        setShowChatDialog(false)
  }
    }

    fetchWorkflow()
  }, [workflowId, pendingChatWorkflowId])

  if (currentView === 'stacks') {
    return (
      <StacksView
        onSelectStack={handleSelectStack}
        onOpenChat={handleOpenStackChat}
      />
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBackToStacks}
              className="text-gray-600 hover:text-gray-800 transition-colors"
            >
              ← Back to Stacks
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-800">Docr Canvas</h1>
              <p className="text-gray-600">Build your RAG pipeline visually</p>
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 flex">
        <Toolbar 
          workflowId={workflowId}
          setWorkflowId={setWorkflowId}
          onNodesChange={setNodes}
        />
        <Canvas
          workflowId={workflowId}
          nodes={nodes}
          edges={edges}
          onNodesChange={setNodes}
          onEdgesChange={setEdges}
          onRun={() => setShowChatDialog(true)}
        />
      </div>

      <ChatDialog
        workflowId={workflowId}
        isOpen={showChatDialog}
        onClose={() => setShowChatDialog(false)}
      />
    </div>
  )
}