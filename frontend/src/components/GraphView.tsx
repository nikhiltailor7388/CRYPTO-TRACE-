import React, {useMemo, useState} from 'react'

const NODE_COLORS: Record<string, string> = {
  victim: '#f97316',
  intermediate: '#38bdf8',
  vasp: '#22c55e',
  mixer: '#f59e0b',
  cluster_member: '#8b5cf6',
  candidate: '#f43f5e',
}

const DISPLAY_EDGE_LIMIT = 80

function shortAddress(value: string) {
  if (!value) return 'Unknown'
  return `${value.slice(0, 6)}…${value.slice(-4)}`
}

export default function GraphView({ data }: { data: any }) {
  const graph = data?.graph || { nodes: [], edges: [] }
  const nodeList = Array.isArray(graph.nodes) ? graph.nodes : []
  const edgeList = Array.isArray(graph.edges) ? graph.edges : []
  const candidateId = String(data?.risk_profile?.fraudster_candidate || '').toLowerCase()
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

  const clusterMap = useMemo(() => {
    const map = new Map<string, string[]>()
    focusedNodeList.forEach((node: any) => {
      if (node.cluster_id) {
        const current = map.get(node.cluster_id) || []
        current.push(node.id)
        map.set(node.cluster_id, current)
      }
    })
    return map
  }, [focusedNodeList])

  const positions = useMemo(() => {
    const out: Record<string, { x: number; y: number }> = {}
    const roots = new Set(focusedNodeList.filter((node: any) => node.type === 'victim').map((node: any) => node.id))
    const depths: Record<string, number> = {}
    roots.forEach((id) => { depths[id] = 0 })
    focusedNodeList.forEach((node: any) => {
      if (Number.isFinite(node.hop_depth)) depths[node.id] = Number(node.hop_depth)
    })
    for (let pass = 0; pass < focusedNodeList.length; pass += 1) {
      focusedEdges.forEach((edge: any) => {
        if (depths[edge.source] !== undefined && (depths[edge.target] === undefined || depths[edge.target] > depths[edge.source] + 1)) depths[edge.target] = depths[edge.source] + 1
      })
    }
    const maxDepth = Math.max(1, ...Object.values(depths))
    const layers: Record<number, any[]> = {}
    focusedNodeList.forEach((node: any) => {
      const depth = depths[node.id] ?? maxDepth
      ;(layers[depth] ||= []).push(node)
    })
    Object.entries(layers).forEach(([depthValue, nodes]) => {
      const depth = Number(depthValue)
      nodes.forEach((node: any, index: number) => {
        out[node.id] = { x: 55 + (450 * depth) / maxDepth, y: 40 + (280 * (index + 1)) / (nodes.length + 1) }
      })
    })
    return out
  }, [focusedEdges, focusedNodeList])

  const selectedNode = focusedNodeList.find((node: any) => node.id === selectedNodeId) || focusedNodeList[0] || null

  if (!nodeList.length) {
    return <div className="graph-shell empty-graph">No graph data available.</div>
  }

  return (
    <div className="graph-investigation">
      <div className="graph-context">
        <div><span className="label">Evidence in view</span><strong>{focusedEdges.length} confirmed transactions</strong></div>
        <div><span className="label">Trace depth</span><strong>Up to {Math.max(0, ...focusedNodeList.map((node: any) => Number(node.hop_depth ?? 0)))} hops</strong></div>
        <div><span className="label">Interaction</span><strong>Select a node for details</strong></div>
      </div>
      <div className="graph-legend" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, marginBottom: 12 }}>
        <span><strong>Legend:</strong></span>
        <span>● Solid circle = wallet address</span>
        <span>→ Solid arrow = direct on-chain transaction</span>
        <span>– – Dashed arrow = probable continuation (confidence shown)</span>
        <span>◌ Dotted outline = wallet cluster</span>
        <span>◆ Distinct colour = VASP / flagged risk node</span>
      </div>

      {edgeList.length > focusedEdges.length ? <div className="empty-table">Focused view: showing {focusedEdges.length} of {edgeList.length} confirmed evidence transactions. The complete evidence ledger remains available below.</div> : null}
      <div className="graph-layout">
        <svg className="graph-shell" viewBox="0 0 560 360" role="img" aria-label="Address relationship map">
          <defs>
            <marker id="trace-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#5eead4" /></marker>
            <marker id="trace-arrow-probable" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L0,6 L7,3 z" fill="#f59e0b" /></marker>
          </defs>
          {[...clusterMap.entries()].map(([clusterId, members]) => {
            const coords = members
              .map((memberId) => positions[memberId])
              .filter(Boolean) as { x: number; y: number }[]
            if (!coords.length) return null
            const minX = Math.min(...coords.map((p) => p.x)) - 30
            const maxX = Math.max(...coords.map((p) => p.x)) + 30
            const minY = Math.min(...coords.map((p) => p.y)) - 30
            const maxY = Math.max(...coords.map((p) => p.y)) + 30
            return (
              <g key={clusterId}>
                <rect
                  x={minX}
                  y={minY}
                  width={Math.max(80, maxX - minX)}
                  height={Math.max(80, maxY - minY)}
                  rx={18}
                  fill="transparent"
                  stroke="#fbbf24"
                  strokeDasharray="4 4"
                  strokeWidth="2"
                />
                <text x={minX + 8} y={minY + 16} fill="#fbbf24" fontSize="10">{clusterId}</text>
              </g>
            )
          })}

          {focusedEdges.map((edge: any) => {
            const source = positions[edge.source]
            const target = positions[edge.target]
            if (!source || !target) return null
            const isProbable = edge.edge_type === 'probable_mixer' || edge.edge_type === 'probable_dex'
            const parallelEdges = focusedEdges.filter((candidate: any) => candidate.source === edge.source && candidate.target === edge.target)
            const parallelIndex = parallelEdges.findIndex((candidate: any) => candidate.id === edge.id)
            const curve = parallelEdges.length > 1 ? (parallelIndex - (parallelEdges.length - 1) / 2) * 14 : 0
            const midX = (source.x + target.x) / 2
            const midY = (source.y + target.y) / 2 - 12 + curve
            const label = `${Number(edge.amount || 0).toFixed(3)} ${edge.asset || 'ETH'}`
            return (
              <g key={edge.id || `${edge.source}-${edge.target}`}>
                <path
                  d={`M ${source.x} ${source.y} Q ${midX} ${midY + 12} ${target.x} ${target.y}`}
                  fill="none"
                  stroke={isProbable ? '#f59e0b' : '#5eead4'}
                  strokeWidth="2.2"
                  strokeDasharray={isProbable ? '6 6' : '0'}
                  markerEnd={`url(#${isProbable ? 'trace-arrow-probable' : 'trace-arrow'})`}
                  opacity="0.9"
                />
                <title>{`${edge.tx_hash || 'transaction'}: ${label}${edge.confidence ? ` / confidence ${edge.confidence}%` : ''}`}</title>
                {focusedEdges.length <= 30 ? <text x={midX} y={midY} fill="#dbeafe" fontSize="10" textAnchor="middle">{label}</text> : null}
              </g>
            )
          })}

          {focusedNodeList.map((node: any) => {
            const point = positions[node.id]
            if (!point) return null
            const isSelected = selectedNodeId === node.id
            const isCandidate = String(node.id).toLowerCase() === candidateId
            const fill = NODE_COLORS[isCandidate ? 'candidate' : node.type] || '#38bdf8'
            return (
              <g key={node.id} onClick={() => setSelectedNodeId(node.id)} style={{ cursor: 'pointer' }}>
                <circle
                  cx={point.x}
                  cy={point.y}
                  r={isSelected ? 18 : 14}
                  fill={fill}
                  stroke="#f8fafc"
                  strokeWidth={isSelected ? 3 : 2}
                  opacity="0.96"
                />
                <text x={point.x} y={point.y + 4} fill="#f8fafc" fontSize="9" textAnchor="middle">
                  {shortAddress(node.id)}
                </text>
                {node.hop_depth !== undefined && node.hop_depth !== null ? <text x={point.x} y={point.y + 28} fill="#cbd5e1" fontSize="9" textAnchor="middle">Hop {node.hop_depth}</text> : null}
                <title>{`${node.id} | ${isCandidate ? 'heuristic candidate, not proof' : node.type} | total_in=${node.total_in} | total_out=${node.total_out}`}</title>
              </g>
            )
          })}
        </svg>

        {selectedNode ? (
          <aside className="panel" style={{ padding: 16, minHeight: 200 }}>
            <div className="panel-header inline-header">
              <span className="eyebrow">Node details</span>
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              <div><strong>Label:</strong> {selectedNode.label}</div>
              <div><strong>Type:</strong> {selectedNode.type}</div>
              <div><strong>Hop:</strong> {selectedNode.hop_depth ?? 'not reachable from source'}</div>
              {String(selectedNode.id).toLowerCase() === candidateId ? <div><strong>Candidate:</strong> heuristic lead, not proof of identity or ownership</div> : null}
              <div><strong>Address:</strong> {selectedNode.id}</div>
              <div><strong>Cluster:</strong> {selectedNode.cluster_id || 'none'}</div>
              <div><strong>Total in:</strong> {Number(selectedNode.total_in || 0).toFixed(6)}</div>
              <div><strong>Total out:</strong> {Number(selectedNode.total_out || 0).toFixed(6)}</div>
            </div>
          </aside>
        ) : null}
      </div>
    </div>
  )
}
