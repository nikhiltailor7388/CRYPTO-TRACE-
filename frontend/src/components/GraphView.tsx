import React, {useMemo, useState} from 'react'

const NODE_COLORS: Record<string, string> = {
  victim: '#f97316',
  intermediate: '#38bdf8',
  vasp: '#22c55e',
  mixer: '#f59e0b',
  cluster_member: '#8b5cf6',
}

function shortAddress(value: string) {
  if (!value) return 'Unknown'
  return `${value.slice(0, 6)}…${value.slice(-4)}`
}

export default function GraphView({ data }: { data: any }) {
  const graph = data?.graph || { nodes: [], edges: [] }
  const nodeList = Array.isArray(graph.nodes) ? graph.nodes : []
  const edgeList = Array.isArray(graph.edges) ? graph.edges : []
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const clusterMap = useMemo(() => {
    const map = new Map<string, string[]>()
    nodeList.forEach((node: any) => {
      if (node.cluster_id) {
        const current = map.get(node.cluster_id) || []
        current.push(node.id)
        map.set(node.cluster_id, current)
      }
    })
    return map
  }, [nodeList])

  const positions = useMemo(() => {
    const out: Record<string, { x: number; y: number }> = {}
    nodeList.forEach((node: any, index: number) => {
      const angle = nodeList.length > 1 ? (Math.PI * 2 * index) / nodeList.length : 0
      const radius = nodeList.length > 1 ? 150 : 0
      out[node.id] = {
        x: 280 + Math.cos(angle) * radius,
        y: 180 + Math.sin(angle) * radius,
      }
    })
    return out
  }, [nodeList])

  const selectedNode = nodeList.find((node: any) => node.id === selectedNodeId) || nodeList[0] || null

  if (!nodeList.length) {
    return <div className="graph-shell empty-graph">No graph data available.</div>
  }

  return (
    <div>
      <div className="graph-legend" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', fontSize: 12, marginBottom: 12 }}>
        <span><strong>Legend:</strong></span>
        <span>● Solid circle = wallet address</span>
        <span>→ Solid arrow = direct on-chain transaction</span>
        <span>– – Dashed arrow = probable continuation (confidence shown)</span>
        <span>◌ Dotted outline = wallet cluster</span>
        <span>◆ Distinct colour = VASP / flagged risk node</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 2fr) minmax(220px, 300px)', gap: 16 }}>
        <svg className="graph-shell" viewBox="0 0 560 360" role="img" aria-label="Address relationship map">
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

          {edgeList.map((edge: any) => {
            const source = positions[edge.source]
            const target = positions[edge.target]
            if (!source || !target) return null
            const isProbable = edge.edge_type === 'probable_mixer' || edge.edge_type === 'probable_dex'
            const midX = (source.x + target.x) / 2
            const midY = (source.y + target.y) / 2 - 12
            const label = `${Number(edge.amount || 0).toFixed(3)} ${edge.asset || 'ETH'}`
            return (
              <g key={edge.id || `${edge.source}-${edge.target}`}>
                <line
                  x1={source.x}
                  y1={source.y}
                  x2={target.x}
                  y2={target.y}
                  stroke={isProbable ? '#f59e0b' : '#5eead4'}
                  strokeWidth="2.2"
                  strokeDasharray={isProbable ? '6 6' : '0'}
                  opacity="0.9"
                />
                <title>{`${edge.tx_hash || 'transaction'}: ${label}${edge.confidence ? ` / confidence ${edge.confidence}%` : ''}`}</title>
                <text x={midX} y={midY} fill="#dbeafe" fontSize="10" textAnchor="middle">{label}</text>
              </g>
            )
          })}

          {nodeList.map((node: any, index: number) => {
            const point = positions[node.id]
            if (!point) return null
            const isSelected = selectedNodeId === node.id
            const fill = NODE_COLORS[node.type] || '#38bdf8'
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
                <title>{`${node.id} | total_in=${node.total_in} | total_out=${node.total_out}`}</title>
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
