import React, {useMemo} from 'react'

function formatAddress(address:string) {
  return address.length > 14 ? `${address.slice(0, 7)}…${address.slice(-6)}` : address
}

function formatAmount(value: unknown, asset: string) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return `0 ${asset}`
  return `${amount.toLocaleString(undefined, {maximumFractionDigits: 8})} ${asset}`
}

export default function GraphView({data, path, asset, evidence}:{data:any, path:string[], asset:string, evidence:any[]}){
  const graph = data || {nodes: [], edges: []}
  const orderedPath = path?.length ? path : graph.nodes || []
  const positions = useMemo(() => {
    const count = orderedPath.length
    const spacing = count > 1 ? 500 / (count - 1) : 250
    return Object.fromEntries(orderedPath.map((node, index) => [
      node,
      {x: count > 1 ? 30 + index * spacing : 250, y: 160},
    ]))
  }, [orderedPath])

  if (!orderedPath.length) {
    return <div className="graph-shell empty-graph">No bounded trace path available.</div>
  }

  const edgeFor = (from:string, to:string) =>
    evidence.find((edge:any) => edge.from === from && edge.to === to)

  return (
    <div>
      <svg className="graph-shell" viewBox="0 0 560 320" role="img"
        aria-label={`Bounded transaction path: ${orderedPath.map(formatAddress).join(' to ')}`}>
        {orderedPath.slice(0, -1).map((from, index) => {
          const to = orderedPath[index + 1]
          const source = positions[from]
          const target = positions[to]
          const edge = edgeFor(from, to)
          return (
            <g key={`${from}-${to}`}>
              <line x1={source.x + 20} y1={source.y} x2={target.x - 20} y2={target.y}
                stroke="#67e8f9" strokeWidth="3" markerEnd="url(#arrow)" />
              <text x={(source.x + target.x) / 2} y="125" fill="#dbeafe" fontSize="11" textAnchor="middle">
                Hop {index + 1} · {formatAmount(edge?.amount, asset)}
              </text>
            </g>
          )
        })}
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="#67e8f9" />
          </marker>
        </defs>
        {orderedPath.map((node, index) => {
          const point = positions[node]
          const role = index === 0 ? 'Source' : index === orderedPath.length - 1 ? 'Destination' : `Hop ${index}`
          return (
            <g key={node}>
              <circle cx={point.x} cy={point.y} r="22"
                fill={index === 0 ? '#f97316' : index === orderedPath.length - 1 ? '#34d399' : '#8b5cf6'}
                stroke="#f8fafc" strokeWidth="2" />
              <text x={point.x} y="205" fill="#f8fafc" fontSize="11" textAnchor="middle">{role}</text>
              <text x={point.x} y="220" fill="#94a3b8" fontSize="10" textAnchor="middle">{formatAddress(node)}</text>
            </g>
          )
        })}
      </svg>
      <p className="path-summary">
        {orderedPath.map((node, index) => `${index === 0 ? 'Source' : `Hop ${index}`} ${formatAddress(node)}`).join(' → ')}
      </p>
    </div>
  )
}
