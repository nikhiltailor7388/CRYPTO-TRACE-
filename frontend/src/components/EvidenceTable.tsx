import React from 'react'

function formatAddress(addr:string) {
  if (!addr) return '—'
  return addr.length > 12 ? `${addr.slice(0, 6)}…${addr.slice(-6)}` : addr
}

function formatAmount(value: unknown, asset: string) {
  const amount = Number(value || 0)
  if (!Number.isFinite(amount)) return `0 ${asset}`
  return `${amount.toLocaleString(undefined, {maximumFractionDigits: 8})} ${asset}`
}

export default function EvidenceTable({evidence, asset}:{evidence:any[], asset:string}){
  if(!evidence || evidence.length===0) return <div className="empty-table">No evidence for this case yet.</div>

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Tx hash</th>
            <th>From</th>
            <th>To</th>
            <th>Amount</th>
            <th>Traceable</th>
            <th>VASP</th>
            <th>Signal</th>
          </tr>
        </thead>
        <tbody>
          {evidence.map((e:any)=> (
            <tr key={e.tx_hash || `${e.from}-${e.to}`}>
              <td><a href={e.explorer_url || '#'} target="_blank" rel="noreferrer">{(e.tx_hash||'').slice(0, 12)}</a></td>
              <td>{formatAddress(e.from)}</td>
              <td>{formatAddress(e.to)}</td>
              <td>{formatAmount(e.amount, asset)}</td>
              <td>{formatAmount(e.traceable_amount, asset)}</td>
              <td>
                <div className="vasp-cell">
                  <span className={`tag ${e.vasp && e.vasp !== 'UNKNOWN' ? 'vasp' : 'neutral'}`}>
                    {e.vasp || 'UNKNOWN'}
                  </span>
                  {e.vasp && e.vasp !== 'UNKNOWN' && (e.confidence || e.source) ? (
                    <small>{e.confidence || 'Unrated'} · {e.source || 'Source unavailable'}{e.source_date ? ` · ${e.source_date}` : ''}</small>
                  ) : null}
                </div>
              </td>
              <td>
                <span className={`tag ${Number(e.traceable_amount || 0) > 0 ? 'positive' : 'neutral'}`}>
                  {Number(e.traceable_amount || 0) > 0 ? 'Traceable' : 'Unclassified'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
