import React, {useMemo, useState} from 'react'

const NODE_COLORS: Record<string, string> = { source: '#f97316', intermediate: '#38bdf8', destination: '#a78bfa', vasp: '#22c55e', bridge: '#f59e0b', cluster: '#8b5cf6', lead: '#f43f5e' }
const DISPLAY_EDGE_LIMIT = 100

function shortAddress(value: string) {
  if (!value) return 'Unknown'
  return value.length > 12 ? `${value.slice(0, 6)}…${value.slice(-4)}` : value
}
function edgeIsCrossChain(edge: any) {
  return Boolean(edge?.source_chain && edge?.destination_chain && edge.source_chain !== edge.destination_chain)
}

export default function GraphView({ data }: { data: any }) {
  const graph = data?.graph || { nodes: [], edges: [] }
  const nodeList = useMemo(() => (Array.isArray(graph.nodes) ? graph.nodes : []).map((node: any) => typeof node === 'string' ? {
    id: node,
    label: node,
    type: node === (data?.source_wallet || data?.wallets?.[0]?.address) ? 'victim' : 'intermediate',
  } : node), [data?.source_wallet, data?.wallets, graph.nodes])
  const edgeList = useMemo(() => {
    const evidenceByHash = new Map((data?.evidence || []).map((item: any) => [item.tx_hash, item]))
    return (Array.isArray(graph.edges) ? graph.edges : []).map((edge: any) => {
      if (!Array.isArray(edge)) return edge
      const [source, target, txHash] = edge
      const evidence = evidenceByHash.get(txHash) || {}
      return { source, target, tx_hash: txHash, id: txHash || `${source}-${target}`, amount: evidence.amount, asset: evidence.asset, confidence: evidence.confidence, hop: evidence.hop }
    })
  }, [data?.evidence, graph.edges])
  const candidateId = String(data?.risk_profile?.fraudster_candidate || '').toLowerCase()
  const destinationIds = useMemo(() => new Set((data?.destination_wallets || []).map((id: string) => String(id).toLowerCase())), [data?.destination_wallets])
  const bridgeIds = useMemo(() => new Set(edgeList.filter(edgeIsCrossChain).flatMap((edge: any) => [String(edge.source).toLowerCase(), String(edge.target).toLowerCase()])), [edgeList])
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const focusedEdges = useMemo(() => {
    const pathPairs = new Set<string>()
    const path = data?.risk_profile?.suspicious_path || []
    for (let index = 0; index < path.length - 1; index += 1) pathPairs.add(`${String(path[index]).toLowerCase()}|${String(path[index + 1]).toLowerCase()}`)
    return [...edgeList].sort((left: any, right: any) => {
      const leftPriority = pathPairs.has(`${String(left.source).toLowerCase()}|${String(left.target).toLowerCase()}`) ? 1 : 0
      const rightPriority = pathPairs.has(`${String(right.source).toLowerCase()}|${String(right.target).toLowerCase()}`) ? 1 : 0
      return rightPriority - leftPriority || Number(right.amount || 0) - Number(left.amount || 0)
    }).slice(0, DISPLAY_EDGE_LIMIT)
  }, [data?.risk_profile?.suspicious_path, edgeList])

  const focusedNodeList = useMemo(() => {
    const ids = new Set<string>()
    focusedEdges.forEach((edge: any) => { ids.add(edge.source); ids.add(edge.target) })
    nodeList.forEach((node: any) => { if (node.type === 'victim' || String(node.id).toLowerCase() === candidateId) ids.add(node.id) })
    return nodeList.filter((node: any) => ids.has(node.id))
  }, [candidateId, focusedEdges, nodeList])

  const positions = useMemo(() => {
    const out: Record<string, { x: number; y: number }> = {}
    const depths: Record<string, number> = {}
    focusedNodeList.filter((node: any) => node.type === 'victim').forEach((node: any) => { depths[node.id] = 0 })
    focusedNodeList.forEach((node: any) => { if (Number.isFinite(node.hop_depth)) depths[node.id] = Number(node.hop_depth) })
    for (let pass = 0; pass < focusedNodeList.length; pass += 1) focusedEdges.forEach((edge: any) => {
      if (depths[edge.source] !== undefined && (depths[edge.target] === undefined || depths[edge.target] > depths[edge.source] + 1)) depths[edge.target] = depths[edge.source] + 1
    })
    const maxDepth = Math.max(1, ...Object.values(depths))
    const layers: Record<number, any[]> = {}
    focusedNodeList.forEach((node: any) => { (layers[depths[node.id] ?? maxDepth] ||= []).push(node) })
    Object.entries(layers).forEach(([depthValue, nodes]) => nodes.forEach((node: any, index: number) => {
      out[node.id] = { x: 74 + (572 * Number(depthValue)) / maxDepth, y: 74 + (300 * (index + 1)) / (nodes.length + 1) }
    }))
    return out
  }, [focusedEdges, focusedNodeList])

  const roleFor = (node: any) => {
    const id = String(node.id).toLowerCase()
    if (node.type === 'victim') return 'source'
    if (id === candidateId) return 'lead'
    if (node.type === 'vasp') return 'vasp'
    if (bridgeIds.has(id)) return 'bridge'
    if (destinationIds.has(id)) return 'destination'
    if (node.type === 'cluster_member') return 'cluster'
    return 'intermediate'
  }
  const selectedNode = focusedNodeList.find((node: any) => node.id === selectedNodeId) || focusedNodeList[0] || null
  const maxDepth = Math.max(0, ...focusedNodeList.map((node: any) => Number(node.hop_depth ?? 0)))

  if (!nodeList.length) return <div className="graph-shell empty-graph"><div><strong>No saved flow graph</strong><span>The investigation has no recorded wallet relationships to visualize.</span></div></div>

  return <div className="graph-investigation">
    <div className="graph-context">
      <div><span className="label">Recorded transactions</span><strong>{focusedEdges.length} in view</strong></div>
      <div><span className="label">Trace depth</span><strong>{maxDepth} hop{maxDepth === 1 ? '' : 's'} reached</strong></div>
      <div><span className="label">Observed endpoints</span><strong>{destinationIds.size || 0} recorded</strong></div>
    </div>
    <div className="graph-legend" aria-label="Graph legend">
      <span><i className="legend-dot source" />Source</span><span><i className="legend-dot intermediate" />Observed wallet</span>
      {destinationIds.size ? <span><i className="legend-dot destination" />Recorded destination</span> : null}
      {focusedNodeList.some((node: any) => node.type === 'vasp') ? <span><i className="legend-dot vasp" />VASP/entity</span> : null}
      {bridgeIds.size ? <span><i className="legend-dot bridge" />Cross-chain boundary</span> : null}
      {candidateId ? <span><i className="legend-dot lead" />Investigative lead</span> : null}
    </div>
    {edgeList.length > focusedEdges.length ? <div className="empty-table">Focused view: showing {focusedEdges.length} of {edgeList.length} recorded transactions. The complete ledger remains available below.</div> : null}
    <div className="graph-layout">
      <svg className="graph-shell" viewBox="0 0 720 440" role="img" aria-label="Directional wallet relationship map">
        <defs><marker id="trace-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#5eead4" /></marker><marker id="trace-arrow-probable" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#f59e0b" /></marker></defs>
        {Array.from({ length: maxDepth + 1 }, (_, depth) => <text key={depth} x={74 + (572 * depth) / Math.max(1, maxDepth)} y="28" fill="#94a3b8" fontSize="11" textAnchor="middle">{depth === 0 ? 'SOURCE' : `HOP ${depth}`}</text>)}
        {focusedEdges.map((edge: any) => {
          const source = positions[edge.source]; const target = positions[edge.target]
          if (!source || !target) return null
          const isProbable = edge.edge_type === 'probable_mixer' || edge.edge_type === 'probable_dex'
          const parallels = focusedEdges.filter((item: any) => item.source === edge.source && item.target === edge.target)
          const curve = parallels.length > 1 ? (parallels.findIndex((item: any) => item.id === edge.id) - (parallels.length - 1) / 2) * 14 : 0
          const midX = (source.x + target.x) / 2; const midY = (source.y + target.y) / 2 - 13 + curve
          const label = `${Number(edge.amount || 0).toFixed(3)} ${edge.asset || data?.chain || 'asset'}`
          return <g key={edge.id || `${edge.source}-${edge.target}`}><path d={`M ${source.x} ${source.y} Q ${midX} ${midY + 13} ${target.x} ${target.y}`} fill="none" stroke={isProbable ? '#f59e0b' : '#5eead4'} strokeWidth="2.2" strokeDasharray={isProbable ? '6 6' : '0'} markerEnd={`url(#${isProbable ? 'trace-arrow-probable' : 'trace-arrow'})`} opacity="0.9" /><title>{`${edge.tx_hash || 'transaction'}: ${label}${edge.confidence ? ` / confidence ${edge.confidence}%` : ''}`}</title>{focusedEdges.length <= 30 ? <text x={midX} y={midY} fill="#dbeafe" fontSize="10" textAnchor="middle">{label}</text> : null}</g>
        })}
        {focusedNodeList.map((node: any) => {
          const point = positions[node.id]; if (!point) return null
          const role = roleFor(node); const isSelected = selectedNodeId === node.id
          return <g key={node.id} className="graph-node" onClick={() => setSelectedNodeId(node.id)}><circle cx={point.x} cy={point.y} r={isSelected ? 19 : 15} fill={NODE_COLORS[role]} stroke="#f8fafc" strokeWidth={isSelected ? 3 : 2} opacity="0.98" /><text x={point.x} y={point.y + 4} fill="#f8fafc" fontSize="9" textAnchor="middle">{shortAddress(node.id)}</text><text x={point.x} y={point.y + 30} fill="#cbd5e1" fontSize="9" textAnchor="middle">{role === 'source' ? 'Source' : node.hop_depth !== undefined && node.hop_depth !== null ? `Hop ${node.hop_depth}` : role}</text><title>{`${node.id} | ${role} | total_in=${node.total_in} | total_out=${node.total_out}`}</title></g>
        })}
      </svg>
      {selectedNode ? <aside className="panel graph-node-details"><div className="panel-header inline-header"><span className="eyebrow">Selected wallet</span><h3>{roleFor(selectedNode)}</h3></div><dl><div><dt>Address</dt><dd><code>{selectedNode.id}</code></dd></div><div><dt>Saved role</dt><dd>{selectedNode.type || 'observed wallet'}</dd></div><div><dt>Trace position</dt><dd>{selectedNode.hop_depth ?? 'Not reachable from source'}</dd></div>{String(selectedNode.id).toLowerCase() === candidateId ? <div className="lead-note">Investigative lead only. It is not proof of identity, ownership, or unlawful activity.</div> : null}<div><dt>Cluster</dt><dd>{selectedNode.cluster_id || 'None recorded'}</dd></div><div><dt>Observed totals</dt><dd>In {Number(selectedNode.total_in || 0).toFixed(6)} · Out {Number(selectedNode.total_out || 0).toFixed(6)}</dd></div></dl></aside> : null}
    </div>
  </div>
}
