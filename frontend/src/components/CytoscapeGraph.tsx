import { useRef, useEffect, useState, useCallback } from 'react'
import cytoscape, { Core, EventObject } from 'cytoscape'
import type { GraphResponse, GraphNode, GraphEdge } from '@/types'
import { Maximize2, Minimize2, RotateCcw } from 'lucide-react'

// ─── Entity type visual encoding: color + shape + abbreviation ───
// Each type has THREE independent identifiers so colorblind users
// can distinguish nodes by shape and label even without color perception.

const ENTITY_ENCODING: Record<string, {
  color: string
  shape: string      // Cytoscape shape name
  abbr: string       // 2-3 letter abbreviation for inside the node
  legendLabel: string
}> = {
  PERSON:         { color: '#4a7fbf', shape: 'ellipse',      abbr: 'PR', legendLabel: 'Person' },
  PHONE:          { color: '#5a9e6f', shape: 'diamond',      abbr: 'PH', legendLabel: 'Phone' },
  EMAIL:          { color: '#8b6db5', shape: 'tag',           abbr: 'EM', legendLabel: 'Email' },
  IP_ADDRESS:     { color: '#c0544f', shape: 'hexagon',       abbr: 'IP', legendLabel: 'IP Address' },
  UPI_ID:         { color: '#c49a3c', shape: 'star',          abbr: 'UP', legendLabel: 'UPI ID' },
  VEHICLE:        { color: '#c77840', shape: 'triangle',      abbr: 'VH', legendLabel: 'Vehicle' },
  DEVICE:         { color: '#3a9aa0', shape: 'rectangle',     abbr: 'DV', legendLabel: 'Device' },
  LOCATION:       { color: '#bf6b8a', shape: 'round-rectangle', abbr: 'LO', legendLabel: 'Location' },
  ORGANIZATION:   { color: '#6e7fbf', shape: 'square',        abbr: 'OG', legendLabel: 'Organization' },
  BANK_ACCOUNT:   { color: '#4aaa6a', shape: 'rectangle',     abbr: 'BK', legendLabel: 'Bank Account' },
  SOCIAL_ACCOUNT: { color: '#a87cc5', shape: 'ellipse',       abbr: 'SA', legendLabel: 'Social' },
  URL:            { color: '#7a8a9a', shape: 'tag',           abbr: 'UL', legendLabel: 'URL' },
  CASE_REFERENCE: { color: '#6a7a8a', shape: 'round-rectangle', abbr: 'CR', legendLabel: 'Case Ref' },
}

const FALLBACK_ENCODING = { color: '#7a8a9a', shape: 'ellipse', abbr: '??', legendLabel: 'Unknown' }

const NODE_BORDER = '#1c2030'
const EDGE_COLOR = '#3a4050'
const EDGE_LABEL_COLOR = '#5a6070'
const SELECTED_BORDER = '#d4a853'

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
          source_evidence_number: n.source_evidence_number ?? null,
          mention_text: n.mention_text ?? null,
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
        // ─── Node: shape + color encode type, name label below ───
        {
          selector: 'node',
          style: {
            // Name label below the node
            label: 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            color: '#c8cad0',
            'font-size': '10px',
            'font-family': '"JetBrains Mono", monospace',
            'text-margin-y': 7,
            'text-wrap': 'ellipsis',
            'text-max-width': '80px',
            // Shape encodes entity type (colorblind-accessible)
            shape: (ele: any) => {
              const enc = ENTITY_ENCODING[ele.data('entity_type')] || FALLBACK_ENCODING
              return enc.shape
            },
            // Color reinforces entity type
            'background-color': (ele: any) => {
              const enc = ENTITY_ENCODING[ele.data('entity_type')] || FALLBACK_ENCODING
              return enc.color
            },
            // Size encodes prominence on a REAL hierarchy: degree arrives
            // normalized to 0-100, so map it across 26-52px (the old linear
            // 24+degree*2 scale saturated at the 56px clamp for 11 of 13
            // nodes on the demo case, collapsing the visual ranking).
            width: (ele: any) => Math.round(26 + (Math.min(100, Math.max(0, ele.data('degree') || 0)) / 100) * 26),
            height: (ele: any) => Math.round(26 + (Math.min(100, Math.max(0, ele.data('degree') || 0)) / 100) * 26),
            'border-width': 1.5,
            'border-color': NODE_BORDER,
          } as any,
        },
        // ─── Edge style ───
        {
          selector: 'edge',
          style: {
            width: 1.2,
            'line-color': EDGE_COLOR,
            'line-opacity': 0.7,
            'target-arrow-color': EDGE_COLOR,
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(label)',
            'font-size': '7px',
            'font-family': '"JetBrains Mono", monospace',
            color: EDGE_LABEL_COLOR,
            'text-rotation': 'autorotate',
          } as any,
        },
        // ─── Selected node — gold glow pulse ───
        {
          selector: 'node:selected',
          style: {
            'border-width': 2.5,
            'border-color': SELECTED_BORDER,
            'background-color': SELECTED_BORDER,
            color: '#0d1117',
            'overlay-opacity': 0.08,
            'overlay-color': '#d4a853',
          } as any,
        },
        // ─── High-degree node (hub) — subtle outer glow ───
        {
          selector: 'node[degree >= 5]',
          style: {
            'border-width': 2,
            'border-color': 'rgba(212, 168, 83, 0.5)',
            'border-opacity': 0.5,
          } as any,
        },
        // ─── Hovered node ───
        {
          selector: 'node:active',
          style: {
            'border-width': 2,
            'border-color': '#ffffff',
          } as any,
        },
      ],
      layout: {
        name: 'cose',
        animate: true,
        animationDuration: 800,
        animationEasing: 'cubic-bezier(0.16, 1, 0.3, 1)',
        nodeRepulsion: () => 10000,
        idealEdgeLength: () => 140,
        gravity: 0.25,
        numIter: 400,
        padding: 40,
        randomize: false,
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

  // Build legend entries — show each unique entity type present in the graph
  const presentTypes = new Set(graph.nodes.map(n => n.entity_type))
  const legendEntries = Object.entries(ENTITY_ENCODING)
    .filter(([type]) => presentTypes.has(type))

  return (
    <div className={`relative ${expanded ? 'fixed inset-0 z-50 bg-charcoal' : ''}`}>
      {/* Controls */}
      <div className="absolute right-2 top-2 z-10 flex gap-1">
        <button onClick={handleFit} className="rounded bg-charcoal-light/90 p-1.5 text-gray-400 hover:text-white hover:bg-charcoal transition-colors" title="Fit">
          <Maximize2 className="h-3.5 w-3.5" />
        </button>
        <button onClick={handleReset} className="rounded bg-charcoal-light/90 p-1.5 text-gray-400 hover:text-white hover:bg-charcoal transition-colors" title="Reset layout">
          <RotateCcw className="h-3.5 w-3.5" />
        </button>
        <button onClick={() => setExpanded(!expanded)} className="rounded bg-charcoal-light/90 p-1.5 text-gray-400 hover:text-white hover:bg-charcoal transition-colors" title="Toggle fullscreen">
          {expanded ? <Minimize2 className="h-3.5 w-3.5" /> : <Maximize2 className="h-3.5 w-3.5" />}
        </button>
      </div>

      {/* Legend — shape + color + label for each entity type */}
      <div className="absolute left-2 top-2 z-10 rounded bg-charcoal-light/95 p-2.5 text-[9px] font-mono border border-charcoal max-w-[220px]">
        <p className="mb-1.5 text-gray-400 uppercase tracking-wider">Entity Types</p>
        <div className="space-y-0.5">
          {legendEntries.map(([type, enc]) => (
            <div key={type} className="flex items-center gap-1.5">
              {/* Shape indicator — matches Cytoscape shape */}
              <ShapeIcon shape={enc.shape} color={enc.color} />
              <span className="text-gray-300">{enc.legendLabel}</span>
              <span className="text-gray-600 ml-auto">{enc.abbr}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 pt-1.5 border-t border-charcoal">
          <p className="text-gray-500 text-[8px]">Shape + color encode type</p>
        </div>
      </div>

      {/* Stats bar */}
      <div className="absolute bottom-2 left-2 z-10 rounded bg-charcoal-light/90 px-2 py-1 text-[9px] text-gray-500 font-mono">
        {graph.stats.node_count} nodes · {graph.stats.edge_count} edges · {graph.stats.connected_components || 1} component(s)
      </div>

      {/* Graph container — dark canvas with fade-in reveal */}
      <div
        ref={containerRef}
        className={`w-full rounded bg-charcoal graph-reveal ${expanded ? 'h-full' : 'h-[600px]'}`}
      />

      {/* Node details panel */}
      {selectedNode && (
        <div className="absolute right-2 top-12 z-10 w-60 rounded-sm bg-charcoal-light p-3 border border-charcoal text-xs font-mono">
          <div className="flex items-center gap-2 mb-2">
            <ShapeIcon
              shape={ENTITY_ENCODING[selectedNode.entity_type]?.shape || 'ellipse'}
              color={ENTITY_ENCODING[selectedNode.entity_type]?.color || '#7a8a9a'}
              size={14}
            />
            <h3 className="font-bold text-white">{selectedNode.label}</h3>
          </div>
          <div className="space-y-1 text-gray-400">
            <p><span className="text-gray-500">Type:</span> <span className="text-gray-300">{selectedNode.entity_type}</span></p>
            <p><span className="text-gray-500">Confidence:</span> <span className="text-dossier">{(selectedNode.confidence * 100).toFixed(0)}%</span></p>
            <p><span className="text-gray-500">Degree:</span> <span className="text-gray-300">{selectedNode.degree}</span></p>
            <p><span className="text-gray-500">Betweenness:</span> <span className="text-gray-300">{selectedNode.betweenness}</span></p>
            <p><span className="text-gray-500">Cases:</span> <span className="text-gray-300">{selectedNode.cases?.join(', ') || 'N/A'}</span></p>
            {selectedNode.source_evidence_number && (
              <p>
                <span className="text-gray-500">Source:</span>{' '}
                <span className="text-dossier">{selectedNode.source_evidence_number}</span>
                {selectedNode.mention_text && (
                  <span className="block pl-1 text-[10px] text-gray-500 italic">“{selectedNode.mention_text}”</span>
                )}
              </p>
            )}
          </div>
          <p className="mt-2 text-[9px] text-dossier-dim leading-relaxed">
            Network prominence is an analytical indicator and does not establish criminal responsibility.
          </p>
        </div>
      )}
    </div>
  )
}

// ─── SVG Shape Icons for the legend ───
// These render the same shapes used in Cytoscape so the legend is a visual key.

function ShapeIcon({ shape, color, size = 8 }: { shape: string; color: string; size?: number }) {
  const s = size

  switch (shape) {
    case 'ellipse':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <ellipse cx="5" cy="5" rx="4.5" ry="4.5" fill={color} />
        </svg>
      )
    case 'diamond':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 9.5,5 5,9.5 0.5,5" fill={color} />
        </svg>
      )
    case 'tag':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="1,1 9,1 9,7 5,9 1,7" fill={color} />
        </svg>
      )
    case 'hexagon':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 9,2.5 9,7.5 5,9.5 1,7.5 1,2.5" fill={color} />
        </svg>
      )
    case 'star':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 6.2,3.5 9.5,3.8 7,6 7.8,9.5 5,7.5 2.2,9.5 3,6 0.5,3.8 3.8,3.5" fill={color} />
        </svg>
      )
    case 'triangle':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <polygon points="5,0.5 9.5,9 0.5,9" fill={color} />
        </svg>
      )
    case 'square':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <rect x="1" y="1" width="8" height="8" fill={color} />
        </svg>
      )
    case 'round-rectangle':
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <rect x="1" y="1" width="8" height="8" rx="2" fill={color} />
        </svg>
      )
    case 'rectangle':
    default:
      return (
        <svg width={s} height={s} viewBox="0 0 10 10" className="shrink-0">
          <rect x="0.5" y="1.5" width="9" height="7" fill={color} />
        </svg>
      )
  }
}
