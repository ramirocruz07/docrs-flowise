'use client'
import React from 'react'
import { Handle, Position, NodeProps } from 'reactflow'
import { FileText, Scissors, Layers, Database, MessageCircle } from 'lucide-react'

interface CustomNodeData {
  label: string;
  type: string;
}

const getNodeIcon = (type: string): React.ReactElement => {
  const iconProps = { size: 16, className: "" };
  
  switch (type) {
    case 'pdf_loader':
      return <FileText {...iconProps} className="text-blue-500" />
    case 'text_splitter':
      return <Scissors {...iconProps} className="text-green-500" />
    case 'embeddings':
      return <Layers {...iconProps} className="text-purple-500" />
    case 'vector_store':
      return <Database {...iconProps} className="text-orange-500" />
    case 'qa_chain':
      return <MessageCircle {...iconProps} className="text-red-500" />
    default:
      return <div className="w-4 h-4 bg-gray-400 rounded" />
  }
}

const CustomNode: React.FC<NodeProps<CustomNodeData>> = ({ data }) => {
  return (
    <div className="px-4 py-2 shadow-md rounded-md bg-white border-2 border-gray-200 min-w-40">
      {/* Input Handles */}
      <Handle
        type="target"
        position={Position.Left}
        className="w-3 h-3 bg-blue-500"
      />
      
      {/* Node Content */}
      <div className="flex items-center space-x-2">
        {getNodeIcon(data.type)}
        <div className="text-sm font-medium">{data.label}</div>
      </div>
      
      {/* Output Handles */}
      <Handle
        type="source"
        position={Position.Right}
        className="w-3 h-3 bg-green-500"
      />
    </div>
  )
}

export default CustomNode