import type { ComponentType, Dispatch, SetStateAction } from 'react';
import type { Edge, Node } from 'reactflow';

export type WorkflowNodeData = {
  label: string;
  type: string;
};

export type WorkflowNode = Node<WorkflowNodeData>;

export type WorkflowEdge = Edge;

export interface NodeType {
  type: string;
  name: string;
  icon: ComponentType<{ size?: number; className?: string }>;
  description: string;
  inputs: string[];
  outputs: string[];
}

export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface WorkflowCreateResponse {
  workflow_id: string;
  name: string;
  message: string;
}

export interface NodeAddResponse {
  node_id: string;
  node_type: string;
  inputs: string[];
  outputs: string[];
}

export interface WorkflowExecuteResponse {
  success: boolean;
  results: {
    answer?: string;
    [key: string]: unknown;
  };
  execution_order: string[];
}

export interface ToolbarProps {
  workflowId: string | null;
  setWorkflowId: (id: string | null) => void;
  onNodesChange: Dispatch<SetStateAction<WorkflowNode[]>>;
}

export interface CanvasProps {
  workflowId: string | null;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  onNodesChange: Dispatch<SetStateAction<WorkflowNode[]>>;
  onEdgesChange: Dispatch<SetStateAction<WorkflowEdge[]>>;
  onRun?: () => void;
}

export interface StacksViewProps {
  onSelectStack: (stackId: string) => void;
  onOpenChat: (stackId: string) => void;
}