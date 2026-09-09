import React, { useEffect, useMemo, useRef, useState } from 'react'

type Transaction = { tx_hash?: string; from?: string; to?: string; amount?: number; asset?: string; timestamp?: string; source_chain?: string; destination_chain?: string; chain?: string; vasp?: string; explorer_url?: string }
type Node = { id: string; type: string; label: string; hop_depth?: number; cluster_id?: string | null; total_in: number; total_out: number }
type Relationship = { id: string; source: string; target: string; asset: string; sourceChain: string; destinationChain: string; amount: number; transactions: Transaction[]; hop?: number }

const COLORS: Record<string, string> = { victim: '#f97316', intermediate: '#38bdf8', vasp: '#22c55e', cluster_member: '#8b5cf6', candidate: '#f43f5e' }
const MAX_OVERVIEW_RELATIONSHIPS = 72

function identity(value: unknown, chain: string) {
  const text = String(value || '').trim()
  return String(chain || '').toUpperCase() === 'TRON' ? text : text.toLowerCase()
}
function short(value: string) { return value.length > 13 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value || 'Unknown' }
function amount(value: number, asset: string) { return `${value.toLocaleString(undefined, { maximumFractionDigits: Math.abs(value) < 0.001 ? 8 : 4 })} ${asset}` }
function zoomViewport(viewport: { zoom: number; x: number; y: number }, layout: { width: number; height: number }, delta: number) {
  const zoom = Math.max(.65, Math.min(2.2, viewport.zoom + delta))
  const ratio = zoom / viewport.zoom
  const centerX = layout.width / 2; const centerY = layout.height / 2
  return { zoom, x: centerX - (centerX - viewport.x) * ratio, y: centerY - (centerY - viewport.y) * ratio }
}

export default function GraphView({ data }: { data: any }) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  // Node identity is the single selection source of truth. Relationship clicks
  // intentionally do not clear it, so Wallet Details cannot fall back to a
  // stale source selection when an investigator inspects an edge.
  const selectedNode = selectedNodeId
  const setSelectedNode = (nodeId: string | null) => { if (nodeId) setSelectedNodeId(nodeId) }
  const [selectedRelationship, setSelectedRelationship] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)
  const [viewport, setViewport] = useState({ zoom: 1, x: 0, y: 0 })
  const drag = useRef<{ x: number; y: number } | null>(null)
  const svg = useRef<SVGSVGElement | null>(null)
  const chain = String(data?.chain || 'ETH').toUpperCase()

  useEffect(() => {
    setSelectedNodeId(null); setSelectedRelationship(null); setShowAll(false); setViewport({ zoom: 1, x: 0, y: 0 })
  }, [data])

  const model = useMemo(() => {
    const evidence: Transaction[] = Array.isArray(data?.evidence) ? data.evidence.filter((item: Transaction) => item?.from && item?.to) : []
    const rawGraph = data?.graph || {}
    const rawEdges = Array.isArray(rawGraph.edges) ? rawGraph.edges : []
    const transactions: Transaction[] = evidence.length ? evidence : rawEdges.map((edge: any) => Array.isArray(edge)
      ? { from: edge[0], to: edge[1], tx_hash: edge[2], asset: chain }
      : edge).filter((edge: Transaction) => edge?.from || edge?.source)
      .map((edge: any) => ({ ...edge, from: edge.from || edge.source, to: edge.to || edge.target }))
    const source = identity(data?.source_wallet || data?.wallets?.[0]?.address || transactions[0]?.from, chain)
    const rawNodes = Array.isArray(rawGraph.nodes) ? rawGraph.nodes : []
    const rawById = new Map(rawNodes.map((item: any) => {
      const id = typeof item === 'string' ? item : item?.id
      return [identity(id, chain), typeof item === 'string' ? { id } : item]
    }))
    const clusters = Array.isArray(data?.wallet_clusters) ? data.wallet_clusters : []
    const clusterById = new Map<string, string>()
    clusters.forEach((cluster: any) => (cluster.members || []).forEach((member: string) => clusterById.set(identity(member, chain), cluster.id)))
    const groups = new Map<string, Relationship>()
    transactions.forEach((transaction) => {
      const sourceId = identity(transaction.from, transaction.source_chain || transaction.chain || chain)
      const targetId = identity(transaction.to, transaction.destination_chain || transaction.chain || chain)
      const asset = String(transaction.asset || chain)
      const sourceChain = String(transaction.source_chain || transaction.chain || chain)
      const destinationChain = String(transaction.destination_chain || transaction.chain || chain)
      const key = [sourceId, targetId, asset, sourceChain, destinationChain].join('|')
      const relationship = groups.get(key) || { id: `relationship-${key}`, source: sourceId, target: targetId, asset, sourceChain, destinationChain, amount: 0, transactions: [] }
      relationship.amount += Number(transaction.amount || 0)
      relationship.transactions.push(transaction)
      groups.set(key, relationship)
    })
    const relationships = [...groups.values()]
    const adjacency = new Map<string, string[]>()
    relationships.forEach((relationship) => adjacency.set(relationship.source, [...(adjacency.get(relationship.source) || []), relationship.target]))
    const hops = new Map<string, number>()
    if (source) hops.set(source, 0)
    const queue = source ? [source] : []
    while (queue.length) {
      const current = queue.shift()!
      for (const next of adjacency.get(current) || []) {
        const depth = (hops.get(current) || 0) + 1
        if (!hops.has(next) || depth < hops.get(next)!) { hops.set(next, depth); queue.push(next) }
      }
    }
    relationships.forEach((relationship) => { relationship.hop = hops.has(relationship.source) ? hops.get(relationship.source)! + 1 : undefined })
    const ids = new Set<string>([...rawById.keys(), ...relationships.flatMap((relationship) => [relationship.source, relationship.target])])
    const vaspIds = new Set(transactions.filter((transaction) => transaction.vasp && String(transaction.vasp).toUpperCase() !== 'UNKNOWN').flatMap((transaction) => [identity(transaction.from, transaction.source_chain || transaction.chain || chain), identity(transaction.to, transaction.destination_chain || transaction.chain || chain)]))
    const candidate = identity(data?.risk_profile?.fraudster_candidate, chain)
    const nodes: Node[] = [...ids].map((id) => {
      const raw = rawById.get(id) || {}
      const totalIn = relationships.filter((relationship) => relationship.target === id).reduce((sum, relationship) => sum + relationship.amount, 0)
      const totalOut = relationships.filter((relationship) => relationship.source === id).reduce((sum, relationship) => sum + relationship.amount, 0)
      const type = id === source ? 'victim' : id === candidate ? 'candidate' : vaspIds.has(id) ? 'vasp' : clusterById.has(id) ? 'cluster_member' : 'intermediate'
      const hopDepth = hops.get(id) ?? raw.hop_depth
      return { id, label: raw.label || (type === 'victim' ? 'Source wallet' : type === 'vasp' ? 'VASP / entity' : `Observed wallet${hopDepth === undefined ? '' : ` — Hop ${hopDepth}`}`), type, cluster_id: raw.cluster_id || clusterById.get(id) || null, hop_depth: hopDepth, total_in: totalIn, total_out: totalOut }
    })
    const maxDegree = Math.max(0, ...nodes.map((node) => relationships.filter((relationship) => relationship.source === node.id || relationship.target === node.id).length))
    const branchFactor = Math.max(0, ...[...adjacency.values()].map((targets) => new Set(targets).size))
    const complexity = nodes.length <= 2 && relationships.length <= 1 ? 'minimal' : nodes.length <= 14 && relationships.length <= 16 ? 'medium' : nodes.length < 100 && relationships.length < 100 ? 'high' : 'advanced'
    return { nodes, relationships, clusters, source, complexity, maxDegree, branchFactor, transactionCount: transactions.length }
  }, [chain, data])

  const visibleRelationships = useMemo(() => {
    if (showAll || model.relationships.length <= MAX_OVERVIEW_RELATIONSHIPS) return model.relationships
    const score = (relationship: Relationship) => relationship.amount + relationship.transactions.length * 1_000_000 + (relationship.source === model.source ? 100_000_000 : 0)
    return [...model.relationships].sort((left, right) => score(right) - score(left)).slice(0, MAX_OVERVIEW_RELATIONSHIPS)
  }, [model.relationships, model.source, showAll])

  const layout = useMemo(() => {
    const visibleIds = new Set(visibleRelationships.flatMap((relationship) => [relationship.source, relationship.target]))
    if (model.source) visibleIds.add(model.source)
    const nodes = model.nodes.filter((node) => visibleIds.has(node.id))
    const degree = new Map(nodes.map((node) => [node.id, visibleRelationships.filter((relationship) => relationship.source === node.id || relationship.target === node.id).length]))
    const layers = new Map<number, Node[]>()
    nodes.forEach((node) => layers.set(node.hop_depth ?? 999, [...(layers.get(node.hop_depth ?? 999) || []), node]))
    const layerKeys = [...layers.keys()].sort((a, b) => a - b)
    layerKeys.forEach((key) => layers.get(key)!.sort((left, right) => (degree.get(right.id)! - degree.get(left.id)!) || left.id.localeCompare(right.id)))
    for (let pass = 0; pass < 4; pass += 1) {
      layerKeys.forEach((key) => {
        const layer = layers.get(key)!
        layer.sort((left, right) => {
          const center = (node: Node) => {
            const neighbours = visibleRelationships.filter((relationship) => relationship.target === node.id || relationship.source === node.id).map((relationship) => relationship.target === node.id ? relationship.source : relationship.target)
            const positions = neighbours.map((id) => layers.get((nodes.find((node) => node.id === id)?.hop_depth) ?? 999)?.findIndex((node) => node.id === id) ?? 0)
            return positions.length ? positions.reduce((sum, value) => sum + value, 0) / positions.length : degree.get(node.id) || 0
          }
          return center(left) - center(right) || left.id.localeCompare(right.id)
        })
      })
    }
    const compact = model.complexity === 'minimal'
    const maxLayer = Math.max(0, ...layerKeys.filter((key) => key < 999))
    // Each hop receives a band, rather than one fixed x-coordinate. Dense hops
    // are packed into a small grid, retaining the sorted investigative order.
    const bands = layerKeys.map((key) => {
      const layer = layers.get(key)!
      const layerDegree = Math.max(0, ...layer.map((node) => degree.get(node.id) || 0))
      const rows = compact ? 1 : Math.min(7, Math.max(1, Math.ceil(Math.sqrt(layer.length * (layerDegree > 8 ? .9 : .62)))))
      const columns = Math.max(1, Math.ceil(layer.length / rows))
      const contentWidth = (columns - 1) * 96
      const width = compact ? 280 : Math.max(190, contentWidth + 118 + Math.min(96, layerDegree * 3))
      return { key, layer, rows, contentWidth, width, start: 0 }
    })
    let cursor = compact ? 80 : 54
    bands.forEach((band) => { band.start = cursor; cursor += band.width + (compact ? 0 : 38) })
    const maxRows = Math.max(1, ...bands.map((band) => band.rows))
    const width = compact ? 440 : Math.max(620, cursor + 20)
    const height = compact ? 260 : Math.max(390, maxRows * 82 + 150)
    const positions = new Map<string, { x: number; y: number }>()
    bands.forEach((band) => {
      band.layer.forEach((node, index) => {
        if (compact) {
          positions.set(node.id, { x: band.start + (band.key === 0 ? 20 : 150), y: height / 2 })
          return
        }
        const column = Math.floor(index / band.rows)
        const row = index % band.rows
        positions.set(node.id, {
          x: band.start + (band.width - band.contentWidth) / 2 + column * 96,
          y: height / 2 + (row - (band.rows - 1) / 2) * 82
        })
      })
    })
    return { nodes, positions, width, height, maxLayer, bands, compact }
  }, [model, visibleRelationships])

  // These controls alter only the viewport. The layout and investigation data
  // remain stable while zooming, panning, or fitting the current graph.
  const setZoom = (updater: (value: number) => number) => setViewport((value) => zoomViewport(value, layout, updater(value.zoom) - value.zoom))
  const setPan = (next: { x: number; y: number }) => setViewport((value) => ({ ...value, x: next.x, y: next.y }))

  const selectedEdge = visibleRelationships.find((relationship) => relationship.id === selectedRelationship) || null
  const selected = (selectedNodeId ? layout.nodes.find((node) => node.id === selectedNodeId) : null) || layout.nodes.find((node) => node.id === model.source) || null
  const selectedTransactionCount = visibleRelationships.reduce((sum, relationship) => sum + relationship.transactions.length, 0)
  const allVisible = visibleRelationships.length === model.relationships.length

  if (!model.nodes.length) return <div className="graph-shell empty-graph">No recorded wallet relationships are available for this investigation.</div>

  return <div className={`graph-investigation graph-${model.complexity}`}>
    <div className="graph-context">
      <div><span className="label">Investigation graph</span><strong>{model.nodes.length} wallets · {model.relationships.length} relationships</strong></div>
      <div><span className="label">Evidence represented</span><strong>{model.transactionCount} transactions</strong></div>
      <div><span className="label">Structure</span><strong>{layout.maxLayer} hops · max degree {model.maxDegree}</strong></div>
      <div><span className="label">View mode</span><strong>{model.complexity} · branching {model.branchFactor}</strong></div>
    </div>
    <div className="graph-legend"><span><i className="legend-dot source" />Source</span><span><i className="legend-dot intermediate" />Observed wallet</span><span><i className="legend-dot vasp" />VASP/entity</span><span><i className="legend-dot lead" />Investigative lead</span><span>Click a relationship for its underlying evidence.</span></div>
    {!allVisible ? <div className="graph-notice">Overview shows {visibleRelationships.length} of {model.relationships.length} relationships, representing {selectedTransactionCount} of {model.transactionCount} transactions. <button type="button" onClick={() => setShowAll(true)}>Show all relationships</button></div> : model.relationships.length > MAX_OVERVIEW_RELATIONSHIPS ? <div className="graph-notice">Showing all {model.relationships.length} relationships. <button type="button" onClick={() => setShowAll(false)}>Return to focused overview</button></div> : null}
    <div className="graph-layout">
      <div className="graph-canvas-wrap">
        <div className="graph-toolbar"><button type="button" onClick={() => setZoom((value) => Math.max(.65, value - .15))}>−</button><button type="button" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }) }}>Fit view</button><button type="button" onClick={() => setZoom((value) => Math.min(2.2, value + .15))}>+</button></div>
        <svg ref={svg} className="graph-shell adaptive-graph" viewBox={`0 0 ${layout.width} ${layout.height}`} role="img" aria-label="Directional blockchain wallet relationship graph" onWheel={(event) => { event.preventDefault(); setViewport((value) => zoomViewport(value, layout, event.deltaY < 0 ? .12 : -.12)) }} onPointerDown={(event) => { drag.current = { x: event.clientX, y: event.clientY }; event.currentTarget.setPointerCapture(event.pointerId) }} onPointerMove={(event) => { if (!drag.current || !svg.current) return; const bounds = svg.current.getBoundingClientRect(); const dx = (event.clientX - drag.current.x) * layout.width / bounds.width; const dy = (event.clientY - drag.current.y) * layout.height / bounds.height; setViewport((value) => ({ ...value, x: value.x + dx, y: value.y + dy })); drag.current = { x: event.clientX, y: event.clientY } }} onPointerUp={() => { drag.current = null }} onPointerCancel={() => { drag.current = null }}>
          <defs><marker id="flow-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#5eead4" /></marker></defs>
          <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.zoom})`}>
            {!layout.compact && layout.bands.filter((band) => band.key < 999).map((band) => <text key={`hop-${band.key}`} x={band.start + band.width / 2} y="30" className="hop-label">HOP {band.key}</text>)}
            {model.clusters.map((cluster: any) => {
              const points = (cluster.members || []).map((member: string) => layout.positions.get(identity(member, chain))).filter(Boolean) as { x: number; y: number }[]
              if (points.length < 2) return null
              const padding = 30 + Math.min(18, points.length * 2); const minX = Math.min(...points.map((point) => point.x)) - padding; const maxX = Math.max(...points.map((point) => point.x)) + padding; const minY = Math.min(...points.map((point) => point.y)) - padding; const maxY = Math.max(...points.map((point) => point.y)) + padding
              return <g key={cluster.id}><rect x={minX} y={minY} width={maxX - minX} height={maxY - minY} rx="18" className="cluster-boundary" /><text x={minX + 9} y={minY + 15} className="cluster-label">{cluster.id}</text></g>
            })}
            {visibleRelationships.map((relationship) => {
              const source = layout.positions.get(relationship.source); const target = layout.positions.get(relationship.target)
              if (!source || !target) return null
              const selected = selectedRelationship === relationship.id; const dx = target.x - source.x; const dy = target.y - source.y
              const parallel = visibleRelationships.filter((item) => item.source === relationship.source && item.target === relationship.target); const parallelIndex = parallel.findIndex((item) => item.id === relationship.id)
              const curve = Math.max(-42, Math.min(42, dy * .16 + (parallelIndex - (parallel.length - 1) / 2) * 14))
              const labelVisible = model.complexity === 'minimal' || (model.complexity === 'medium' && visibleRelationships.length <= 12) || selected
              return <g key={relationship.id} className="relationship" onClick={(event) => { event.stopPropagation(); setSelectedRelationship(relationship.id); setSelectedNode(null) }}><path d={`M ${source.x} ${source.y} Q ${source.x + dx / 2} ${source.y + dy / 2 + curve} ${target.x} ${target.y}`} markerEnd="url(#flow-arrow)" className={selected ? 'relationship-line selected' : 'relationship-line'} style={{ strokeWidth: Math.min(5, 1.8 + Math.log2(relationship.transactions.length + 1) * .55) }} /><title>{`${relationship.transactions.length} transactions · ${amount(relationship.amount, relationship.asset)}`}</title>{labelVisible ? <text x={source.x + dx / 2} y={source.y + dy / 2 + curve - 7} className="relationship-label">{relationship.transactions.length} tx · {amount(relationship.amount, relationship.asset)}</text> : null}</g>
            })}
            {layout.nodes.map((node) => { const point = layout.positions.get(node.id)!; const isSelected = selectedNode === node.id; const color = COLORS[node.type] || COLORS.intermediate; return <g key={node.id} className={isSelected ? 'graph-node selected-node' : 'graph-node'} onClick={(event) => { event.stopPropagation(); setSelectedNode(node.id); setSelectedRelationship(null) }}><circle cx={point.x} cy={point.y} r={isSelected ? 20 : 16} fill={color} className="wallet-node" /><text x={point.x} y={point.y + 4} className="wallet-address">{short(node.id)}</text><text x={point.x} y={point.y + 32} className="wallet-meta">{node.type === 'victim' ? 'Source' : `Hop ${node.hop_depth ?? '?'}`}</text><title>{`${node.label}: ${node.id}`}</title></g> })}
          </g>
        </svg>
      </div>
      {selectedEdge ? <aside className="panel graph-detail"><span className="eyebrow">Wallet relationship</span><h3>{short(selectedEdge.source)} → {short(selectedEdge.target)}</h3><dl><div><dt>Transactions</dt><dd>{selectedEdge.transactions.length}</dd></div><div><dt>Aggregated amount</dt><dd>{amount(selectedEdge.amount, selectedEdge.asset)}</dd></div><div><dt>Hop</dt><dd>{selectedEdge.hop ?? 'Not reached from source'}</dd></div></dl><strong>Underlying evidence</strong><div className="transaction-list">{selectedEdge.transactions.map((transaction, index) => <div key={`${transaction.tx_hash || 'transaction'}-${index}`}><code>{short(String(transaction.tx_hash || 'transaction'))}</code><span>{amount(Number(transaction.amount || 0), transaction.asset || selectedEdge.asset)}</span></div>)}</div></aside> : selected ? <aside className="panel graph-detail"><span className="eyebrow">Wallet details</span><h3>{selected.label}</h3><dl><div><dt>Address</dt><dd><code>{selected.id}</code></dd></div><div><dt>Hop</dt><dd>{selected.hop_depth ?? 'Not reached from source'}</dd></div><div><dt>Cluster</dt><dd>{selected.cluster_id || 'None recorded'}</dd></div><div><dt>Observed in / out</dt><dd>{selected.total_in.toFixed(6)} / {selected.total_out.toFixed(6)}</dd></div><div><dt>Relationships in view</dt><dd>{visibleRelationships.filter((relationship) => relationship.source === selected.id || relationship.target === selected.id).length}</dd></div></dl></aside> : null}
    </div>
  </div>
}
