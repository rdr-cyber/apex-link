import { useRef, useEffect, useState, useCallback } from 'react'
import cytoscape, { Core, EventObject } from 'cytoscape'
import type { GraphResponse, GraphNode, GraphEdge } from '@/types'
import { Maximize2, Minimize2, RotateCcw } from 'lucide-react'

const ENTITY_COLORS: Record<string, string> = {
  PERSON: '#3b82f6',
  PHONE: '#22c55e',
  EMAIL: '#a855f7',
  IP_ADDRESS: '#ef4444',
  UPI_ID: '#eab308',
  VEHICLE: '#f97316',
  DEVICE: '#06b6d4',
  LOCATION: '#ec4899',
  ORGANIZATION: '#6366f1',
  BANK_ACCOUNT: '#10b981',
  SOCIAL_ACCOUNT: '#8b5cf6',
  URL: '#64748b',
  CASE_REFERENCE: '#78716c',
}

interface Props {
  graph: GraphResponse
  onSelectNode?: (node: GraphNode) => void
  onSelectEdge?: (edge: GraphEdge) => void
}

export function CytoscapeComponent({ graph, onSelectNode, onSelectEdge }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [expanded, setExpanded] = useState(false)

  const initGraph = useCallback(() => {
    if (!containerRef.current || !graph.nodes.length) return

    if (cyRef.current) {
      cyRef.current.destroy()
    }

    const elements = [
      ...graph.nodes.map((n) => ({
        data: {
          id: n.id,
          label: n.label,
          entity_type: n.entity_type,
          confidence: n.confidence,
          degree: n.degree,
          betweenness: n.betweenness,
        },
      })),
      ...graph.edges.map((e) => ({
        data: {
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label,
          relationship_type: e.relationship_type,
          confidence: e.confidence,
        },
      })),
    ]

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: 'node',
          style: {
            label: 'data(label)',
            'background-color': (ele: any) => ENTITY_COLORS[ele.data('entity_type')] || '#94a3b8',
            color: '#1e293b',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'font-size': '10px',
            width: (ele: any) => Math.max(20, Math.min(60, 20 + ele.data('degree') * 2)),
            height: (ele: any) => Math.max(20, Math.min(60, 20 + ele.data('degree') * 2)),
            'border-width': 2,
            'border-color': '#ffffff',
            'text-wrap': 'ellipsis',
            'text-max-width': '80px',
          } as any,
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '8px',
            color: '#94a3b8',
            'text-rotation': 'autorotate',
          } as any,
        },
        {
          selector: 'node:selected',
          style: {
            'border-width': 3,
            'border-color': '#6366f1',
            'background-color': '#6366f1',
            color: '#ffffff',
          },
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        nodeRepulsion: () => 8000,
        idealEdgeLength: () => 120,
        gravity: 0.3,
        numIter: 500,
      } as any,
      minZoom: 0.2,
      maxZoom: 3,
    })

    cy.on('tap', 'node', (evt: EventObject) => {
      const nodeId = evt.target.id()
      const node = graph.nodes.find((n) => n.id === nodeId)
      if (node) {
        setSelectedNode(node)
        onSelectNode?.(node)
      }
    })

    cy.on('tap', 'edge', (evt: EventObject) => {
      const edgeId = evt.target.id()
      const edge = graph.edges.find((e) => e.id === edgeId)
      if (edge) {
        onSelectEdge?.(edge)
      }
    })

    cy.on('tap', (evt: EventObject) => {
      if (evt.target === cy) {
        setSelectedNode(null)
      }
    })

    cyRef.current = cy
  }, [graph, onSelectNode, onSelectEdge])

  useEffect(() => {
    initGraph()
    return () => {
      cyRef.current?.destroy()
    }
  }, [initGraph])

  const handleFit = () => cyRef.current?.fit(undefined, 50)
  const handleReset = () => {
    cyRef.current?.layout({ name: 'cose', animate: true, padding: 50 } as any).run()
  }

  return (
    <div className={`relative ${expanded ? 'fixed inset-0 z-50 bg-white dark:bg-gray-950' : ''}`}>
      {/* Controls */}
      <div className="absolute right-3 top-3 z-10 flex gap-1">
        <button onClick={handleFit} className="rounded-lg bg-white/90 dark:bg-gray-800/90 p-1.5 shadow hover:bg-gray-100 dark:hover:bg-gray-700" title="Fit">
          <Maximize2 className="h-4 w-4" />
        </button>
        <button onClick={handleReset} className="rounded-lg bg-white/90 dark:bg-gray-800/90 p-1.5 shadow hover:bg-gray-100 dark:hover:bg-gray-700" title="Reset layout">
          <RotateCcw className="h-4 w-4" />
        </button>
        <button onClick={() => setExpanded(!expanded)} className="rounded-lg bg-white/90 dark:bg-gray-800/90 p-1.5 shadow hover:bg-gray-100 dark:hover:bg-gray-700" title="Toggle fullscreen">
          {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
        </button>
      </div>

      {/* Legend */}
      <div className="absolute left-3 top-3 z-10 rounded-lg bg-white/90 dark:bg-gray-800/90 p-2 shadow text-xs">
        <p className="mb-1 font-medium">Entity Types</p>
        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5">
          {Object.entries(ENTITY_COLORS).slice(0, 8).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1">
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
              <span>{type.replace(/_/g, ' ')}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div className="absolute bottom-3 left-3 z-10 rounded-lg bg-white/90 dark:bg-gray-800/90 px-3 py-1.5 shadow text-xs text-gray-500">
        {graph.stats.node_count} nodes · {graph.stats.edge_count} edges · {graph.stats.connected_components || 1} component(s)
      </div>

      {/* Graph container */}
      <div
        ref={containerRef}
        className={`w-full border border-gray-200 dark:border-gray-800 rounded-lg bg-gray-50 dark:bg-gray-900 ${expanded ? 'h-full' : 'h-[600px]'}`}
      />

      {/* Node details panel */}
      {selectedNode && (
        <div className="absolute right-3 top-14 z-10 w-64 rounded-lg bg-white dark:bg-gray-900 p-4 shadow-lg border border-gray-200 dark:border-gray-800">
          <h3 className="font-semibold text-sm mb-2">{selectedNode.label}</h3>
          <div className="space-y-1 text-xs">
            <p><span className="text-gray-500">Type:</span> {selectedNode.entity_type}</p>
            <p><span className="text-gray-500">Confidence:</span> {(selectedNode.confidence * 100).toFixed(0)}%</p>
            <p><span className="text-gray-500">Degree:</span> {selectedNode.degree}</p>
            <p><span className="text-gray-500">Betweenness:</span> {selectedNode.betweenness}</p>
            <p><span className="text-gray-500">Cases:</span> {selectedNode.cases?.join(', ') || 'N/A'}</p>
          </div>
          <p className="mt-3 text-[10px] text-amber-600 dark:text-amber-400">
            Network prominence is an analytical indicator and does not establish criminal responsibility.
          </p>
        </div>
      )}
    </div>
  )
}
