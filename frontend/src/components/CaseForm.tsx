import React, {useRef, useState} from 'react'

export default function CaseForm({onResult, onStart, onComplete, authToken}:{onResult:(result:any)=>void, onStart?:()=>void, onComplete?:(result:any)=>void, authToken?:string}){
  const [sourceWallet, setSourceWallet] = useState('')
  // Leaving this blank lets the API create an isolated case for each new
  // trace. A supplied ID remains an explicit request to update that case.
  const [caseId, setCaseId] = useState('')
  const [chain, setChain] = useState('ETH')
  const [txHash, setTxHash] = useState('')
  const [amount, setAmount] = useState('')
  const [currency, setCurrency] = useState('ETH')
  const [maxHops, setMaxHops] = useState(3)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const activeRequest = useRef<AbortController | null>(null)
  const requestSequence = useRef(0)

  const handleTrace = async ()=>{
    const networkWallets = Array.from(new Set([...(sourceWallet ? [sourceWallet] : [])]))
    if (networkWallets.length === 0) {
      setError('Enter a valid victim/suspect wallet address.')
      return
    }

    // A late response must never replace the result of a newer trace.
    activeRequest.current?.abort()
    const requestId = ++requestSequence.current
    setLoading(true)
    setError('')
    onStart?.()
    const controller = new AbortController()
    activeRequest.current = controller
    const timeoutId = window.setTimeout(() => controller.abort(), 70000)

    try {
      const payload = {
        case_id: caseId.trim() || undefined,
        case_name: `Case ${caseId}`,
        chain,
        wallets: networkWallets,
        source_wallet: sourceWallet || networkWallets[0],
        tx_hash: txHash || undefined,
        amount: amount ? Number(amount) : undefined,
        currency: currency || undefined,
        max_hops: maxHops,
      }

      const res = await fetch('/trace', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authToken ? { Authorization: 'Bearer ' + authToken } : {}),
        },
        body: JSON.stringify(payload),
        signal: controller.signal,
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
      if (requestId === requestSequence.current) {
        onResult(j)
        onComplete?.(j)
      }
    } catch (err:any) {
      if (requestId === requestSequence.current) {
        setError(err?.name === 'AbortError' ? 'Trace timed out after 70 seconds. Reduce hops or retry with a more specific wallet/transaction.' : (err.message || 'Trace failed'))
      }
    } finally {
      window.clearTimeout(timeoutId)
      if (requestId === requestSequence.current) {
        activeRequest.current = null
        setLoading(false)
      }
    }
  }

  return (
    <div className="form-panel-inner">
      <div className="panel-header">
        <span className="eyebrow">Investigation</span>
        <h2>Trace wallet</h2>
      </div>

      <div className="field-group">
        <label>Case ID (optional)</label>
        <input value={caseId} onChange={e=>setCaseId(e.target.value)} placeholder="Auto-generated for each new trace" />
      </div>

      <div className="field-group">
        <label>From wallet address</label>
        <input value={sourceWallet} onChange={e=>setSourceWallet(e.target.value)} placeholder={chain === 'TRON' ? 'T...' : '0x...'} />
      </div>

      <div className="field-group">
        <label>Transaction hash / ID (optional)</label>
        <input value={txHash} onChange={e=>setTxHash(e.target.value)} placeholder="0x... (tx hash)" />
      </div>

      <div className="field-group">
        <label>Amount (optional)</label>
        <input value={amount} onChange={e=>setAmount(e.target.value)} placeholder="e.g. 1.5" />
      </div>

      <div className="field-group">
        <label>Currency / asset (optional)</label>
          <select value={currency} onChange={e=>setCurrency(e.target.value)}>
            <option value="ETH">ETH</option>
            <option value="TRX">TRX</option>
          <option value="USDT">USDT</option>
          <option value="USDC">USDC</option>
        </select>
      </div>

      <div className="inline-fields">
        <div className="field-group compact">
          <label>Chain</label>
          <select value={chain} onChange={e=>{
            const selectedChain = e.target.value
            setChain(selectedChain)
            // Keep the optional asset filter valid when switching networks.
            // This matters when the investigator supplies a transaction ID.
            setCurrency(selectedChain === 'TRON' ? 'TRX' : (currency === 'TRX' ? 'ETH' : currency))
          }}>
            <option value="ETH">ETH</option>
            <option value="BSC">BSC</option>
            <option value="POLYGON">POLYGON</option>
            <option value="BASE">BASE</option>
            <option value="TRON">TRON</option>
          </select>
        </div>

        <div className="field-group compact">
          <label>Max hops</label>
          <input type="number" min={1} max={5} value={maxHops} onChange={e=>setMaxHops(Number(e.target.value || 1))} />
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <button className="primary-btn" onClick={handleTrace} disabled={loading}>
        {loading ? 'Retrieving on-chain evidence...' : 'Run trace'}
      </button>
    </div>
  )
}
