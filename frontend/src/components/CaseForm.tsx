import React, {useState} from 'react'

export default function CaseForm({onResult, authToken}:{onResult:(result:any)=>void, authToken?:string}){
  const [sourceWallet, setSourceWallet] = useState('')
  const [targetWallet, setTargetWallet] = useState('')
  const [walletCluster, setWalletCluster] = useState('')
  const [caseId, setCaseId] = useState('INV-001')
  const [chain, setChain] = useState('ETH')
  const [maxHops, setMaxHops] = useState(3)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleTrace = async ()=>{
    const wallets = walletCluster.split(/[\n,]+/).map(v=>v.trim()).filter(Boolean)
    const networkWallets = Array.from(new Set([...(sourceWallet ? [sourceWallet] : []), ...(targetWallet ? [targetWallet] : []), ...wallets]))
    if (!caseId.trim() || networkWallets.length === 0) {
      setError('Enter a case ID and at least one valid Ethereum wallet address.')
      return
    }

    setLoading(true)
    setError('')

    try {
      const payload = {
        case_id: caseId,
        case_name: `Case ${caseId}`,
        chain,
        wallets: networkWallets,
        source_wallet: sourceWallet || networkWallets[0],
        target_wallet: targetWallet || networkWallets[networkWallets.length - 1],
        max_hops: maxHops,
      }

      const res = await fetch('/trace', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: 'Bearer ' + authToken } : {}),
        },
        body: JSON.stringify(payload),
      })

      const textBody = await res.text()
      if (!textBody) {
        throw new Error('Backend returned an empty response. Check whether the API server is running.')
      }

      let j
      try {
        j = JSON.parse(textBody)
      } catch {
        throw new Error('Server returned an invalid response. Check the backend and the active frontend port.')
      }

      if (!res.ok) {
        throw new Error(j?.detail || 'Trace request failed')
      }
      onResult(j)
    } catch (err:any) {
      setError(err.message || 'Trace failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="form-panel-inner">
      <div className="panel-header">
        <span className="eyebrow">Investigation</span>
        <h2>Trace wallet</h2>
      </div>

      <div className="field-group">
        <label>Case ID</label>
        <input value={caseId} onChange={e=>setCaseId(e.target.value)} placeholder="INV-001" />
      </div>

      <div className="field-group">
        <label>Reported wallet</label>
        <input value={sourceWallet} onChange={e=>setSourceWallet(e.target.value)} placeholder="0x..." />
      </div>

      <div className="field-group">
        <label>Destination wallet</label>
        <input value={targetWallet} onChange={e=>setTargetWallet(e.target.value)} placeholder="0x..." />
      </div>

      <div className="field-group">
        <label>Wallet cluster</label>
        <textarea value={walletCluster} onChange={e=>setWalletCluster(e.target.value)} rows={3} placeholder="0x...\n0x..." />
      </div>

      <div className="inline-fields">
        <div className="field-group compact">
          <label>Chain</label>
          <select value={chain} onChange={e=>setChain(e.target.value)}>
            <option value="ETH">ETH</option>
            <option value="BSC">BSC</option>
            <option value="POLYGON">POLYGON</option>
            <option value="BASE">BASE</option>
          </select>
        </div>

        <div className="field-group compact">
          <label>Max hops</label>
          <input type="number" min={1} max={3} value={maxHops} onChange={e=>setMaxHops(Number(e.target.value || 1))} />
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <button className="primary-btn" onClick={handleTrace} disabled={loading}>
        {loading ? 'Tracing?' : 'Trace wallet'}
      </button>
    </div>
  )
}
