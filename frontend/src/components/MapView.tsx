import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { GraphResponse, GraphNode } from '@/types'

// ─────────────────────────────────────────────────────────────────────────────
// MapView — additive rendering path for the Network tab.
// Shares GraphResponse data with CytoscapeGraph but renders independently:
// a bug here cannot affect the graph view (separate component, no shared
// mutable state, no cytoscape involvement).
//
// Geodata: LOCATION entities are plotted via a fixed demo lookup table —
// approximate city/area coordinates, NOT precise geocoding. Adequate for the
// synthetic demo dataset; production deployments would require a real
// geocoding service. Entities without a known location are simply not plotted.
// ─────────────────────────────────────────────────────────────────────────────

/** Demo-grade approximate coordinates. Deliberately area-level, not exact. */
const LOCATION_COORDS: Record<string, [number, number]> = {
  'andheri west mumbai': [19.1364, 72.8296],
  'bandra east mumbai': [19.0607, 72.8362],
  'connaught place delhi': [28.6315, 77.2167],
  'cyber hub gurgaon': [28.4949, 77.0886],
  // normalized-with-space variants
  'andheri west, mumbai': [19.1364, 72.8296],
  'bandra east, mumbai': [19.0607, 72.8362],
  'connaught place, delhi': [28.6315, 77.2167],
  'cyber hub, gurgaon': [28.4949, 77.0886],
}

const ENTITY_COLOR: Record<string, string> = {
  PERSON: '#4a7fbf',
  PHONE: '#5a9e6f',
  EMAIL: '#8b6db5',
  IP_ADDRESS: '#c0544f',
  UPI_ID: '#c49a3c',
  VEHICLE: '#c77840',
  DEVICE: '#3a9aa0',
  LOCATION: '#bf6b8a',
  ORGANIZATION: '#6e7fbf',
  BANK_ACCOUNT: '#4aaa6a',
  SOCIAL_ACCOUNT: '#a87cc5',
  URL: '#7a8a9a',
  CASE_REFERENCE: '#6a7a8a',
}

const ENTITY_ABBR: Record<string, string> = {
  PERSON: 'PR', PHONE: 'PH', EMAIL: 'EM', IP_ADDRESS: 'IP', UPI_ID: 'UP',
  VEHICLE: 'VH', DEVICE: 'DV', LOCATION: 'LO', ORGANIZATION: 'OG',
  BANK_ACCOUNT: 'BK', SOCIAL_ACCOUNT: 'SA', URL: 'UL', CASE_REFERENCE: 'CR',
}

/** Shape path per entity type — mirrors CytoscapeGraph's shape coding. */
const ENTITY_SHAPE_PATH: Record<string, string> = {
  PERSON: 'M10 0 C15.5 0 20 4.5 20 10 C20 15.5 15.5 20 10 20 C4.5 20 0 15.5 0 10 C0 4.5 4.5 0 10 0 Z', // ellipse
  PHONE: 'M10 0 L20 10 L10 20 L0 10 Z',                                    // diamond
  EMAIL: 'M2 0 L18 0 L18 13 L10 19 L2 13 Z',                               // tag
  IP_ADDRESS: 'M10 0 L19 5 L19 15 L10 20 L1 15 L1 5 Z',                    // hexagon
  UPI_ID: 'M10 0 L12.4 7.2 L20 7.6 L14 12.4 L16 19.5 L10 15.2 L4 19.5 L6 12.4 L0 7.6 L7.6 7.2 Z', // star
  VEHICLE: 'M10 0 L20 19 L0 19 Z',                                          // triangle
  LOCATION: 'M3 0 L17 0 L17 15 Q17 18 14 19 L6 19 Q3 18 3 15 Z',           // round-rect
  ORGANIZATION: 'M1 1 L19 1 L19 19 L1 19 Z',                                // square
  BANK_ACCOUNT: 'M1 3 L19 3 L19 17 L1 17 Z',                                // rectangle
  DEVICE: 'M1 3 L19 3 L19 17 L1 17 Z',
}

function markerIcon(entityType: string): L.DivIcon {
  const color = ENTITY_COLOR[entityType] || '#7a8a9a'
  const path = ENTITY_SHAPE_PATH[entityType] // undefined → square fallback
  const shape = path
    ? `<path d="${path}" fill="${color}" fill-opacity="0.92" stroke="#1c2030" stroke-width="1.5"/>`
    : `<rect x="1" y="3" width="18" height="14" fill="${color}" fill-opacity="0.92" stroke="#1c2030" stroke-width="1.5"/>`
  const abbr = ENTITY_ABBR[entityType] || '??'
  return L.divIcon({
    className: 'map-node-marker',
    html: `<svg width="24" height="24" viewBox="0 0 20 20">${shape}
             <text x="10" y="13" text-anchor="middle" font-size="7" font-weight="700"
               font-family="JetBrains Mono, monospace" fill="#0d1117">${abbr}</text>
           </svg>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  })
}

function locationMarkerIcon(label: string): L.DivIcon {
  // Locations get the gold-ringed treatment: they anchor the map narrative
  return L.divIcon({
    className: 'map-node-marker map-node-location',
    html: `<svg width="26" height="26" viewBox="0 0 20 20">
             <path d="M3 0 L17 0 L17 15 Q17 18 14 19 L6 19 Q3 18 3 15 Z"
               fill="#bf6b8a" fill-opacity="0.92" stroke="#d4a853" stroke-width="1.8"/>
             <text x="10" y="13" text-anchor="middle" font-size="7" font-weight="700"
               font-family="JetBrains Mono, monospace" fill="#0d1117">LO</text>
           </svg>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  })
}

interface Props {
  graph: GraphResponse
}

/** Resolve an entity to coordinates, or null if it has no plotable location. */
function resolveCoords(node: GraphNode): [number, number] | null {
  if (node.entity_type === 'LOCATION') {
    const key = node.label.toLowerCase().trim()
    return LOCATION_COORDS[key] ?? null
  }
  return null
}

export function MapView({ graph }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layerRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current, {
      center: [21.5, 77.5],
      zoom: 5,
      zoomControl: true,
      attributionControl: true,
    })
    // Dark basemap — Esri World Dark Gray Canvas: free, no API key, and
    // matches the charcoal workstation canvas. (CARTO dark tiles now require
    // an API key and watermark keyless requests; standard OSM tiles are light.)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Tiles &copy; Esri — Source: Esri, HERE, Garmin, &copy; OpenStreetMap contributors',
      maxZoom: 16,
    }).addTo(map)
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}', {
      attribution: '',
      maxZoom: 16,
    }).addTo(map)
    layerRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      layerRef.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layer = layerRef.current
    if (!map || !layer) return
    layer.clearLayers()

    // Only entities with resolvable coordinates are plotted — no fake positions.
    const placed = graph.nodes
      .map((n) => ({ node: n, coords: resolveCoords(n) }))
      .filter((p): p is { node: GraphNode; coords: [number, number] } => p.coords !== null)

    if (!placed.length) return

    const byId = new Map(placed.map((p) => [p.node.id, p]))
    const plottedIds = new Set(placed.map((p) => p.node.id))

    // Edges drawn only between two geographically-placed nodes
    for (const e of graph.edges) {
      const a = byId.get(e.source)
      const b = byId.get(e.target)
      if (!a || !b) continue
      L.polyline(
        [a.coords, b.coords],
        { color: '#d4a853', weight: 1.5, opacity: 0.7, dashArray: '5 6' },
      ).addTo(layer)
    }

    for (const { node, coords } of placed) {
      const m = L.marker(coords, {
        icon: node.entity_type === 'LOCATION' ? locationMarkerIcon(node.label) : markerIcon(node.entity_type),
        title: node.label,
      }).addTo(layer)
      m.bindPopup(
        `<div style="font-family:'JetBrains Mono',monospace;font-size:11px;min-width:160px">
           <strong>${node.label}</strong><br/>
           <span style="color:#666">${node.entity_type.replace(/_/g, ' ')}</span><br/>
           <span style="color:#666">confidence:</span> ${(node.confidence * 100).toFixed(0)}%<br/>
           <span style="color:#666">degree:</span> ${node.degree}<br/>
           <span style="color:#666">cases:</span> ${node.cases?.length || 0}
         </div>`,
      )
    }

    // Fit to plotted content once data lands
    const bounds = L.latLngBounds(placed.map((p) => p.coords))
    map.fitBounds(bounds.pad(0.25), { animate: false })
    // ensure tiles render after layout in a tab that just became visible
    setTimeout(() => map.invalidateSize(), 60)
  }, [graph])

  const plottedCount = graph.nodes.filter((n) => resolveCoords(n) !== null).length

  return (
    <div className="relative">
      <div ref={containerRef} className="h-[600px] w-full rounded bg-charcoal" />

      {/* Geoploted count strip — sits above Leaflet's attribution line */}
      <div className="absolute bottom-7 left-2 z-[1000] rounded bg-charcoal-light/90 px-2 py-1 text-[9px] font-mono text-gray-500">
        {plottedCount} of {graph.nodes.length} entities geoplotted · approximate demo coordinates
      </div>

      {/* Legend note — shape coding matches the graph legend; edges are gold */}
      <div className="absolute left-2 top-2 z-[1000] rounded border border-charcoal bg-charcoal-light/95 p-2.5 font-mono text-[9px]">
        <p className="mb-1 uppercase tracking-wider text-gray-400">Map View</p>
        <p className="text-gray-500">
          <span className="text-dossier">──</span> relationship edges
        </p>
        <p className="mt-1 text-gray-600">Only entities with location data are plotted.</p>
      </div>

      {!plottedCount && (
        <div className="pointer-events-none absolute inset-x-0 bottom-16 z-[900] flex items-center justify-center">
          <p className="max-w-xs text-center font-mono text-xs text-gray-400">
            No entities in this case have resolvable location data.
          </p>
        </div>
      )}
    </div>
  )
}
