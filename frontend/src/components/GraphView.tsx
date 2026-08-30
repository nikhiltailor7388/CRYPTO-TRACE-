import React, {useMemo} from 'react'

export default function GraphView({data}:{data:any}){
  const graph = data || { nodes: [], edges: [] }
  const suspectAddresses = (data?.wallets || []).map((w:any) => w.address || w)

  const positions = useMemo(() => {
    const nodes = graph.nodes || []
    const out: Record<string, {x:number, y:number}> = {}
    nodes.forEach((node:string, index:number) => {
      const angle = nodes.length > 1 ? (Math.PI * 2 * index) / nodes.length : 0
      const radius = nodes.length > 1 ? 150 : 0
      out[node] = {
        x: 280 + Math.cos(angle) * radius,
        y: 180 + Math.sin(angle) * radius,
      }
    })
    return out
  }, [graph])

  if (!graph.nodes || graph.nodes.length === 0) {
    return <div className="graph-shell empty-graph">No graph data available.</div>
  }

  return (
    <svg className="graph-shell" viewBox="0 0 560 360" role="img" aria-label="Address relationship map">
      {(graph.edges || []).map((edge:any) => {
        const source = positions[edge[0]]
        const target = positions[edge[1]]
        if (!source || !target) return null
        const midX = (source.x + target.x) / 2
        const midY = (source.y + target.y) / 2 - 12
        return (
          <g key={edge[2] || `${edge[0]}-${edge[1]}`}>
            <line x1={source.x} y1={source.y} x2={target.x} y2={target.y} stroke="#5eead4" strokeWidth="2.2" opacity="0.75" />
            <text x={midX} y={midY} fill="#dbeafe" fontSize="10" textAnchor="middle">tx</text>
          </g>
        )
      })}

      {(graph.nodes || []).map((node:string, index:number) => {
        const point = positions[node]
        const isSuspect = suspectAddresses.includes(node)
        return (
          <g key={node}>
            <circle
              cx={point.x}
              cy={point.y}
              r={isSuspect ? 18 : 15}
              fill={isSuspect ? '#f97316' : index % 2 === 0 ? '#38bdf8' : '#8b5cf6'}
              stroke="#f8fafc"
              strokeWidth="2"
              opacity="0.96"
            />
            <text x={point.x} y={point.y + 4} fill="#f8fafc" fontSize="9" textAnchor="middle">
              {node.slice(0, 6)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
