import React from 'react'

function formatAddress(addr:string) {
  if (!addr) return '—'
  return addr.length > 12 ? `${addr.slice(0, 6)}…${addr.slice(-6)}` : addr
}

export default function EvidenceTable({ evidence, rows }: { evidence?: any[]; rows?: any[] }){
  const items = evidence || rows || []
  if(!items || items.length===0) return <div className="empty-table">No evidence for this case yet.</div>

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>From</th>
            <th>To</th>
            <th>Tx hash</th>
            <th>Amount</th>
            <th>Asset</th>
            <th>Timestamp</th>
            <th>Value at tx time</th>
            <th>VASP</th>
            <th>Explorer</th>
          </tr>
        </thead>
        <tbody>
          {items.map((e:any)=> (
            <tr key={e.tx_hash || `${e.from}-${e.to}`}>
              <td>{formatAddress(e.from)}</td>
              <td>{formatAddress(e.to)}</td>
              <td><a href={e.explorer_url || '#'} target="_blank" rel="noreferrer">{(e.tx_hash||'').slice(0, 12)}</a></td>
              <td>{Number(e.amount || 0).toFixed(3)}</td>
              <td>{e.asset || 'ETH'}</td>
              <td>{e.timestamp || 'unknown'}</td>
              <td>{e.historical_value_usd || 'historical price unavailable'}</td>
              <td>
                <span className={`tag ${e.vasp && e.vasp !== 'UNKNOWN' ? 'vasp' : 'neutral'}`}>
                  {e.vasp || 'UNKNOWN'}
                </span>
              </td>
              <td>
                <a href={e.explorer_url || '#'} target="_blank" rel="noreferrer">Open</a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
