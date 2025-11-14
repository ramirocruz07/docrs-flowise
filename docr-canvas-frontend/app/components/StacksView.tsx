'use client'
import React, { useState, useEffect } from 'react'
import { Plus, ExternalLink, X, MessageCircle } from 'lucide-react'
import axios from 'axios'
import type { StacksViewProps } from '@/types'

interface Stack {
  id: string
  name: string
  description: string
  custom_prompt?: string
  created_at?: string
  updated_at?: string
}

const StacksView: React.FC<StacksViewProps> = ({ onSelectStack, onOpenChat }) => {
  const [stacks, setStacks] = useState<Stack[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newStackName, setNewStackName] = useState('')
  const [newStackDescription, setNewStackDescription] = useState('')
  const [newStackPrompt, setNewStackPrompt] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [deletingStackId, setDeletingStackId] = useState<string | null>(null)

  useEffect(() => {
    loadStacks()
  }, [])

  const loadStacks = async () => {
    try {
      const response = await axios.get('http://localhost:8000/stacks')
      setStacks(response.data.stacks || [])
    } catch (error) {
      console.error('Failed to load stacks:', error)
      setStacks([])
    } finally {
      setLoading(false)
    }
  }

  const handleCreateStack = async () => {
    if (!newStackName.trim()) {
      alert('Please enter a stack name')
      return
    }

    setIsCreating(true)
    try {
      const response = await axios.post('http://localhost:8000/create-workflow', {
        name: newStackName,
        description: newStackDescription,
        custom_prompt: newStackPrompt
      })
      
      setShowCreateModal(false)
      setNewStackName('')
      setNewStackDescription('')
      setNewStackPrompt('')
      await loadStacks()
      onSelectStack(response.data.workflow_id)
    } catch (error) {
      console.error('Failed to create stack:', error)
      alert('Failed to create stack. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleDeleteStack = async (stackId: string) => {
    const stack = stacks.find((s) => s.id === stackId)
    const stackName = stack?.name || 'this stack'
    if (!window.confirm(`Are you sure you want to delete ${stackName}? This action cannot be undone.`)) {
      return
    }
    setDeletingStackId(stackId)
    try {
      await axios.delete(`http://localhost:8000/stack/${stackId}`)
      await loadStacks()
    } catch (error) {
      console.error('Failed to delete stack:', error)
      alert('Failed to delete stack. Please try again.')
    } finally {
      setDeletingStackId(null)
    }
  }

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50">
        <div className="text-gray-500">Loading stacks...</div>
      </div>
    )
  }

  // Show create stack card if no stacks exist
  if (stacks.length === 0) {
    return (
      <div className="h-screen flex flex-col bg-gray-50">
        <header className="bg-white shadow-sm border-b px-6 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-800">My Stacks</h1>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center space-x-2"
            >
              <Plus size={20} />
              <span>New Stack</span>
            </button>
          </div>
        </header>

        <div className="flex-1 flex items-center justify-center p-8">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-md w-full">
            <h2 className="text-2xl font-bold text-gray-800 mb-2">Create New Stack</h2>
            <p className="text-gray-600 mb-6">
              Start building your generative AI apps with our essential tools and frameworks.
            </p>
            <button
              onClick={() => setShowCreateModal(true)}
              className="w-full px-4 py-3 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center space-x-2"
            >
              <Plus size={20} />
              <span>New Stack</span>
            </button>
          </div>
        </div>

        {showCreateModal && (
          <CreateStackModal
            name={newStackName}
            description={newStackDescription}
            customPrompt={newStackPrompt}
            onNameChange={setNewStackName}
            onDescriptionChange={setNewStackDescription}
            onCustomPromptChange={setNewStackPrompt}
            onCreate={handleCreateStack}
            onCancel={() => {
              setShowCreateModal(false)
              setNewStackName('')
              setNewStackDescription('')
              setNewStackPrompt('')
            }}
            isCreating={isCreating}
          />
        )}
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      <header className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-gray-800">My Stacks</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center space-x-2"
          >
            <Plus size={20} />
            <span>New Stack</span>
          </button>
        </div>
      </header>

      <div className="flex-1 overflow-y-auto p-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 max-w-7xl mx-auto">
          {stacks.map((stack) => (
            <div
              key={stack.id}
              className="bg-white rounded-lg shadow-md p-6 flex flex-col hover:shadow-lg transition-shadow"
            >
              <div className="flex items-start justify-between space-x-3">
                <h3 className="text-xl font-bold text-gray-800 mb-2">{stack.name}</h3>
                <button
                  onClick={() => handleDeleteStack(stack.id)}
                  disabled={deletingStackId === stack.id}
                  className="text-gray-400 hover:text-red-500 transition-colors disabled:opacity-50"
                  title="Delete stack"
                >
                  <X size={18} />
                </button>
              </div>
              <p className="text-gray-600 text-sm mb-4">
                {stack.description || 'No description'}
              </p>
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 text-sm text-gray-700 mb-4 flex-1">
                <p className="font-semibold text-gray-800 mb-1">Custom Prompt</p>
                <p className="text-gray-600 whitespace-pre-wrap max-h-32 overflow-y-auto">
                  {stack.custom_prompt ? stack.custom_prompt : 'No custom prompt'}
                </p>
              </div>
              <div className="mt-auto flex space-x-2">
                <button
                  onClick={() => onSelectStack(stack.id)}
                  disabled={deletingStackId === stack.id}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ExternalLink size={16} />
                  <span>Edit</span>
                </button>
                <button
                  onClick={() => onOpenChat(stack.id)}
                  disabled={deletingStackId === stack.id}
                  className="flex-1 px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <MessageCircle size={16} />
                  <span>Chat</span>
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {showCreateModal && (
        <CreateStackModal
          name={newStackName}
          description={newStackDescription}
          customPrompt={newStackPrompt}
          onNameChange={setNewStackName}
          onDescriptionChange={setNewStackDescription}
          onCustomPromptChange={setNewStackPrompt}
          onCreate={handleCreateStack}
          onCancel={() => {
            setShowCreateModal(false)
            setNewStackName('')
            setNewStackDescription('')
            setNewStackPrompt('')
          }}
          isCreating={isCreating}
        />
      )}
    </div>
  )
}

interface CreateStackModalProps {
  name: string
  description: string
  customPrompt: string
  onNameChange: (name: string) => void
  onDescriptionChange: (description: string) => void
  onCustomPromptChange: (prompt: string) => void
  onCreate: () => void
  onCancel: () => void
  isCreating: boolean
}

const CreateStackModal: React.FC<CreateStackModalProps> = ({
  name,
  description,
  customPrompt,
  onNameChange,
  onDescriptionChange,
  onCustomPromptChange,
  onCreate,
  onCancel,
  isCreating
}) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-bold text-gray-800">Create New Stack</h2>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="Enter stack name"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => onDescriptionChange(e.target.value)}
              placeholder="Enter stack description"
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Custom Prompt
            </label>
            <textarea
              value={customPrompt}
              onChange={(e) => onCustomPromptChange(e.target.value)}
              placeholder="Enter a custom prompt or instructions to guide the QA chain"
              rows={5}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 resize-none"
            />
            <p className="mt-1 text-xs text-gray-500">
              This prompt will be prepended to the default question-answer instructions for this stack.
            </p>
          </div>
        </div>

        <div className="flex justify-end space-x-3 p-6 border-t">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onCreate}
            disabled={isCreating || !name.trim()}
            className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            {isCreating ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default StacksView






