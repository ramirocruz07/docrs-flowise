'use client'
import React, { useState, useEffect } from 'react'
import { X, Save, Trash2 } from 'lucide-react'
import axios from 'axios'

interface ConfigField {
  name: string
  label: string
  type: 'text' | 'number' | 'select' | 'toggle'
  default?: string | number | boolean
  required?: boolean
  options?: Array<{ value: string; label: string }>
  min?: number
  max?: number
  step?: number
  conditional?: {
    field: string
    [key: string]: any
  }
}

interface ConfigPanelProps {
  nodeId: string | null
  nodeType: string | null
  workflowId: string | null
  onClose: () => void
  onConfigUpdate: () => void
  onNodeDelete?: (nodeId: string) => void
}

const ConfigPanel: React.FC<ConfigPanelProps> = ({
  nodeId,
  nodeType,
  workflowId,
  onClose,
  onConfigUpdate,
  onNodeDelete
}) => {
  const [config, setConfig] = useState<Record<string, any>>({})
  const [schema, setSchema] = useState<ConfigField[]>([])
  const [loading, setLoading] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (nodeType) {
      fetchConfigSchema()
      fetchCurrentConfig()
    }
  }, [nodeType, nodeId])

  const fetchConfigSchema = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/node-config-schema/${nodeType}`)
      setSchema(response.data.fields || [])
      
      // Initialize config with defaults
      const defaults: Record<string, any> = {}
      response.data.fields?.forEach((field: ConfigField) => {
        if (field.default !== undefined) {
          defaults[field.name] = field.default
        }
      })
      setConfig(defaults)
    } catch (error) {
      console.error('Failed to fetch config schema:', error)
    }
  }

  const fetchCurrentConfig = async () => {
    if (!nodeId || !workflowId) return
    
    try {
      const response = await axios.get(`http://localhost:8000/node/${workflowId}/${nodeId}/config`)
      if (response.data.config) {
        setConfig(response.data.config)
      }
    } catch (error) {
      console.error('Failed to fetch current config:', error)
    }
  }

  const handleFieldChange = (fieldName: string, value: any) => {
    setConfig(prev => {
      const updated = { ...prev, [fieldName]: value }
      
      // Handle conditional fields
      schema.forEach(field => {
        if (field.conditional && field.conditional.field === fieldName) {
          const conditionalValue = field.conditional[value]
          if (conditionalValue && conditionalValue.default !== undefined) {
            updated[field.name] = conditionalValue.default
          }
        }
      })
      
      return updated
    })
  }

  const handleSave = async () => {
    if (!nodeId || !workflowId) return

    setLoading(true)
    try {
      await axios.post(`http://localhost:8000/node/${workflowId}/${nodeId}/config`, {
        config
      })
      onConfigUpdate()
      onClose()
    } catch (error) {
      console.error('Failed to save config:', error)
      alert('Failed to save configuration')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async () => {
    if (!nodeId || !workflowId) return
    const confirmDelete = window.confirm('Delete this node? This action cannot be undone.')
    if (!confirmDelete) return

    setDeleting(true)
    try {
      await axios.delete(`http://localhost:8000/node/${workflowId}/${nodeId}`)
      onNodeDelete?.(nodeId)
      onClose()
    } catch (error) {
      console.error('Failed to delete node:', error)
      alert('Failed to delete node')
    } finally {
      setDeleting(false)
    }
  }

  const renderField = (field: ConfigField) => {
    const value = config[field.name] ?? field.default

    switch (field.type) {
      case 'text':
        return (
          <input
            type="text"
            value={value || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={field.label}
          />
        )
      
      case 'number':
        return (
          <input
            type="number"
            value={value ?? field.default ?? ''}
            onChange={(e) => handleFieldChange(field.name, parseFloat(e.target.value) || 0)}
            min={field.min}
            max={field.max}
            step={field.step || 1}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        )
      
      case 'select':
        return (
          <select
            value={value || field.default || ''}
            onChange={(e) => handleFieldChange(field.name, e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {field.options?.map(option => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        )
      
      case 'toggle':
        return (
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={value ?? field.default ?? false}
              onChange={(e) => handleFieldChange(field.name, e.target.checked)}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">{field.label}</span>
          </label>
        )
      
      default:
        return null
    }
  }

  if (!nodeType) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-800">Configure Node</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {schema.map((field) => (
            <div key={field.name}>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {field.label}
                {field.required && <span className="text-red-500 ml-1">*</span>}
              </label>
              {renderField(field)}
            </div>
          ))}

          {schema.length === 0 && (
            <p className="text-gray-500 text-sm">No configuration options available for this node type.</p>
          )}
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t border-gray-200 px-6 py-4 flex items-center justify-between space-x-3">
          <button
            onClick={handleDelete}
            disabled={deleting || loading}
            className="px-4 py-2 bg-red-100 text-red-600 border border-red-200 rounded-lg hover:bg-red-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
          >
            <Trash2 size={16} />
            <span>{deleting ? 'Deleting...' : 'Delete'}</span>
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center space-x-2 transition-colors"
          >
            <Save size={16} />
            <span>{loading ? 'Saving...' : 'Save'}</span>
          </button>
        </div>
      </div>
    </div>
  )
}

export default ConfigPanel






