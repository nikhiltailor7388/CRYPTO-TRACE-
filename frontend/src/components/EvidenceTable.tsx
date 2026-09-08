import React from 'react'

function formatAddress(value: string) {
  if (!value) return '—'
  return value.length > 12 ? `${value.slice(0, 6)}…${value.slice(-6)}` : value
}

export default function EvidenceTable({ evidence, rows }: { evidence?: any[]; rows?: any[] }) {
  const items = evidence || rows || []
  if (!items.length) return <div className="empty-table">No transaction evidence was recorded for this case.</div>

  return <div className="table-wrap">
    <table>
      <thead><tr><th>From</th><th>To</th><th>Transaction</th><th>Amount</th><th>Asset</th><th>Timestamp</th><th>Value at tx time</th><th>VASP / entity</th><th>Explorer</th></tr></thead>
      <tbody>
        {items.map((item: any, index: number) => <tr key={item.tx_hash || `${item.from}-${item.to}-${index}`}>
          <td className="wallet-cell"><code title={item.from || ''}>{formatAddress(item.from)}</code></td>
          <td className="wallet-cell"><code title={item.to || ''}>{formatAddress(item.to)}</code></td>
          <td className="tx-cell">{item.explorer_url ? <a href={item.explorer_url} target="_blank" rel="noreferrer" title={item.tx_hash || ''}><code>{formatAddress(item.tx_hash || 'unknown')}</code></a> : <code title={item.tx_hash || ''}>{formatAddress(item.tx_hash || 'unknown')}</code>}</td>
          <td className="amount-cell">{Number(item.amount || 0).toLocaleString(undefined, { maximumFractionDigits: 6 })}</td>
          <td><span className="asset-tag">{item.asset || 'ETH'}</span></td>
          <td className="timestamp-cell">{item.timestamp || 'unknown'}</td>
          <td>{item.historical_value_usd || 'Historical price unavailable'}</td>
          <td><span className={`tag ${item.vasp && item.vasp !== 'UNKNOWN' ? 'vasp' : 'neutral'}`}>{item.vasp || 'UNKNOWN'}</span></td>
          <td>{item.explorer_url ? <a href={item.explorer_url} target="_blank" rel="noreferrer">View ↗</a> : 'Unavailable'}</td>
        </tr>)}
      </tbody>
    </table>
  </div>
}
