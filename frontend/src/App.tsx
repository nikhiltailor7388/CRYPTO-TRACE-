import React, {useEffect, useMemo, useState} from 'react'
import CaseForm from './components/CaseForm'
import GraphView from './components/GraphView'
import EvidenceTable from './components/EvidenceTable'

const STORAGE_KEY = 'cryptotrace-auth'

async function readJsonResponse(res: Response) {
  const text = await res.text()
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    throw new Error('Server returned an invalid response. Make sure the backend is running and the browser is using the active frontend port.')
  }
}

type AuthState = {
  token: string
  email: string
  full_name: string
}

export default function App(){
  const [data, setData] = useState<any>(null)
  const [auth, setAuth] = useState<AuthState | null>(() => {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  })
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authForm, setAuthForm] = useState({ email: '', password: '', full_name: '' })
  const [authError, setAuthError] = useState('')
  const [authLoading, setAuthLoading] = useState(false)
  const [caseList, setCaseList] = useState<any[]>([])
  const [casesLoading, setCasesLoading] = useState(false)
  const [caseError, setCaseError] = useState('')

  useEffect(() => {
    if (auth?.token) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
      loadCases(auth.token)
    } else {
      localStorage.removeItem(STORAGE_KEY)
      setCaseList([])
    }
  }, [auth])

  const loadCases = async (token: string) => {
    setCasesLoading(true)
    setCaseError('')
    try {
      const res = await fetch('/cases', { headers: { Authorization: 'Bearer ' + token } })
      const payload = await readJsonResponse(res)
      if (!res.ok) throw new Error(payload?.detail || 'Failed to load cases')
      setCaseList(payload.cases || [])
    } catch (err: any) {
      setCaseError(err.message || 'Failed to load case history')
    } finally {
      setCasesLoading(false)
    }
  }

  const handleAuthSubmit = async () => {
    setAuthLoading(true)
    setAuthError('')
    try {
      const res = await fetch(`/auth/${authMode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: authForm.email,
          password: authForm.password,
          full_name: authForm.full_name,
        })
      })
      const payload = await readJsonResponse(res)
      if (!res.ok) {
        throw new Error(payload?.detail || 'Authentication failed')
      }
      setAuth({ token: payload.token, email: payload.email, full_name: payload.full_name || 'Analyst' })
    } catch (err: any) {
      setAuthError(err.message || 'Authentication failed')
    } finally {
      setAuthLoading(false)
    }
  }

  const handleLoadCase = async (caseId: string) => {
    if (!auth?.token) return
    try {
      const res = await fetch(`/cases/${caseId}`, { headers: { Authorization: 'Bearer ' + auth.token } })
      const payload = await readJsonResponse(res)
      if (!res.ok) throw new Error(payload?.detail || 'Failed to load case')
      setData(payload)
    } catch (err: any) {
      setCaseError(err.message || 'Failed to load case')
    }
  }

  const handleTraceComplete = (result: any) => {
    if (auth?.token) loadCases(auth.token)
    setData(result)
  }

  const summary = useMemo(() => {
    const evidence = data?.evidence || []
    const totalValue = evidence.reduce((sum:any, row:any) => sum + Number(row.amount || 0), 0)
    const traceable = evidence.reduce((sum:any, row:any) => sum + Number(row.traceable_amount || 0), 0)
    const unclassified = evidence.reduce((sum:any, row:any) => sum + Number(row.unclassified_amount || 0), 0)
    return {
      totalValue,
      traceable,
      unclassified,
      vaspMatches: data?.vasp_matches?.length || 0,
      riskScore: data?.summary?.fraud_probability ?? data?.summary?.risk_score ?? 0,
      probability: data?.risk_profile?.overall_probability ?? data?.summary?.fraud_probability ?? data?.summary?.risk_score ?? 0,
      caseId: data?.case_id || 'CASE-001',
      dataSource: data?.data_source || 'no trace yet',
      graphHash: data?.graph_hash || 'N/A',
      fraudster: data?.risk_profile?.fraudster_candidate || 'Not identified',
      suspiciousPath: data?.risk_profile?.suspicious_path || [],
      riskFactors: data?.risk_profile?.risk_factors || [],
      graphMetrics: data?.graph_metrics || {node_count: 0, edge_count: 0, max_degree: 0},
      legalNotice: data?.legal_notice || 'This report identifies the likely exchange endpoint and supporting evidence for a legal request. It does not identify a real person — that requires the exchange\'s own KYC process, which is outside this system\'s scope.',
      checksum: data?.evidence_checksum || 'N/A',
      partial: Boolean(data?.summary?.partial),
      partialReasons: data?.summary?.partial_reasons || [],
      asset: data?.chain === 'TRON' ? 'TRX' : 'ETH',
    }
  }, [data])

  const downloadEvidenceJson = () => {
    if (!data) return
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `evidence-${data.case_id || 'case'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const downloadEvidenceCsv = () => {
    if (!data || !data.evidence) return
    const rows = data.evidence.map((row:any) => ({
      tx_hash: row.tx_hash,
      source_wallet: row.from,
      destination_wallet: row.to,
      amount: row.amount,
      asset: row.asset,
      timestamp: row.timestamp,
      vasp: row.vasp,
      explorer_url: row.explorer_url,
    }))
    const cell = (value: unknown) => `"${String(value ?? '').replaceAll('"', '""')}"`
    const csv = [Object.keys(rows[0] || {}).map(cell).join(','), ...rows.map((r:any) => Object.values(r).map(cell).join(','))].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `evidence-${data.case_id || 'case'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="eyebrow">Blockchain investigations</div>
          <h1>CryptoTrace</h1>
          <p>Trace, preserve, and review public on-chain evidence.</p>
        </div>
        <div className="topbar-actions">
          <div className={`status-pill ${data ? 'active' : ''}`}><span className="status-dot" />{data ? `${summary.dataSource} data` : 'Ready for trace'}</div>
          {auth ? (
            <button className="ghost-btn" onClick={() => setAuth(null)}>Logout</button>
          ) : null}
        </div>
      </header>

      <div className="layout-grid">
        <aside className="panel sidebar-panel">
          {auth ? (
            <>
              <div className="panel-header">
                <span className="eyebrow">Operator</span>
                <h2>{auth.full_name}</h2>
              </div>
              <div className="user-card">
                <strong>{auth.email}</strong>
                <span>Authenticated investigation session</span>
              </div>
              <div className="case-list-box">
                <div className="panel-header inline-header">
                  <span className="eyebrow">Case history</span>
                  <h3>Saved investigations</h3>
                </div>
                {caseError ? <div className="error-banner compact-error">{caseError}</div> : null}
                {casesLoading ? <div className="empty-table">Refreshing saved investigations…</div> : (
                  caseList.length ? (
                    <div className="case-list">
                      {caseList.map((item) => (
                        <button key={item.case_id} className={`case-item ${data?.case_id === item.case_id ? 'active' : ''}`} onClick={() => handleLoadCase(item.case_id)}>
                          <span className="case-item-id">{item.case_id}</span>
                          <span className="case-item-meta"><small>{item.summary?.chain || 'CHAIN'}</small><strong>{item.summary?.fraud_probability ?? item.risk_score ?? 0}% risk</strong></span>
                        </button>
                      ))}
                    </div>
                  ) : <div className="empty-table">No saved cases yet. Run a trace to create a case.</div>
                )}
              </div>
              <CaseForm onResult={setData} onStart={() => setData(null)} onComplete={handleTraceComplete} authToken={auth.token} />
            </>
          ) : (
            <div className="auth-card">
              <div className="panel-header">
                <span className="eyebrow">Secure access</span>
                <h2>{authMode === 'login' ? 'Login' : 'Register'} to CryptoTrace</h2>
              </div>
              <div className="auth-toggle">
                <button className={authMode === 'login' ? 'toggle active' : 'toggle'} onClick={() => setAuthMode('login')}>Login</button>
                <button className={authMode === 'register' ? 'toggle active' : 'toggle'} onClick={() => setAuthMode('register')}>Register</button>
              </div>
              <div className="field-group">
                <label>Email</label>
                <input value={authForm.email} onChange={(e) => setAuthForm({ ...authForm, email: e.target.value })} placeholder="analyst@cryptotrace.io" />
              </div>
              {authMode === 'register' ? (
                <div className="field-group">
                  <label>Full name</label>
                  <input value={authForm.full_name} onChange={(e) => setAuthForm({ ...authForm, full_name: e.target.value })} placeholder="Jane Doe" />
                </div>
              ) : null}
              <div className="field-group">
                <label>Password</label>
                <input type="password" value={authForm.password} onChange={(e) => setAuthForm({ ...authForm, password: e.target.value })} placeholder="????????" />
              </div>
              {authError ? <div className="error-banner">{authError}</div> : null}
              <button className="primary-btn" onClick={handleAuthSubmit} disabled={authLoading}>
                {authLoading ? 'Please wait?' : authMode === 'login' ? 'Login' : 'Create account'}
              </button>
            </div>
          )}
        </aside>

        <main className="main-panel">
          {!data ? (
            <div className="panel empty-panel">
              <h3>Investigation workspace</h3>
              <p>Submit a wallet to trace outbound flow, detect downstream concentration points, and build a structured evidence trail for investigative review.</p>
              <ul>
                <li>Live ETH and TRON retrieval</li>
                <li>Bounded evidence-backed flow analysis</li>
                <li>Risk, VASP, and report review</li>
              </ul>
            </div>
          ) : (
            <>
              <section className="result-hero panel">
                <div>
                  <span className="eyebrow">Investigation result</span>
                  <h2>{data.chain} trace · {summary.caseId}</h2>
                  <p>{data.wallets?.[0]?.address || data.source_wallet || 'Wallet'} · {data.provider || 'Provider'} · {summary.dataSource}</p>
                </div>
                <div className={`risk-orb risk-${summary.probability >= 70 ? 'high' : summary.probability >= 40 ? 'medium' : 'low'}`}>
                  <span>Risk score</span><strong>{summary.probability}%</strong>
                </div>
              </section>

              <div className="stats-grid">
                <div className="stat-card panel">
                  <span className="label">Total value</span>
                  <strong>{summary.totalValue.toFixed(3)} {summary.asset}</strong>
                </div>
                <div className="stat-card panel">
                  <span className="label">Traceable</span>
                  <strong>{summary.traceable.toFixed(3)} {summary.asset}</strong>
                </div>
                <div className="stat-card panel">
                  <span className="label">Unclassified</span>
                  <strong>{summary.unclassified.toFixed(3)} {summary.asset}</strong>
                </div>
                <div className="stat-card panel accent-card">
                  <span className="label">Trace confidence</span>
                  <strong>{summary.riskFactors.some((factor:any) => factor.confidence === 'high') ? 'High' : summary.riskFactors.some((factor:any) => factor.confidence === 'medium') ? 'Medium' : 'Low'}</strong>
                </div>
              </div>

              <div className="case-actions panel">
                <div className="panel small-panel">
                  <span className="label">Case ID</span>
                  <strong>{summary.caseId}</strong>
                </div>
                <div className="panel small-panel">
                  <span className="label">Known VASP hits</span>
                  <strong>{summary.vaspMatches}</strong>
                </div>
                <div className="panel small-panel">
                  <span className="label">{summary.partial ? 'Candidate (partial trace)' : 'Fraudster candidate'}</span>
                  <strong>{summary.fraudster ? summary.fraudster.slice(0, 12) + '?' : 'Unknown'}</strong>
                </div>
                <div className="panel small-panel">
                  <span className="label">Evidence checksum</span>
                  <strong>{summary.graphHash.slice(0, 12)}…</strong>
                </div>
                <div className="panel small-panel">
                  <span className="label">Graph metrics</span>
                  <strong>{summary.graphMetrics.node_count} nodes / {summary.graphMetrics.edge_count} edges</strong>
                </div>
                <a className="download-link" href={data.report_url || `/reports/${data.case_id}.pdf`} target="_blank" rel="noreferrer">
                  PDF report
                </a>
               <a className="download-link" href={data.csv_report_url || `/reports/${data.case_id}.csv`} target="_blank" rel="noreferrer">
                  CSV report
                </a>
               <button className="download-link" type="button" onClick={downloadEvidenceJson}>Evidence JSON</button>
               <button className="download-link" type="button" onClick={downloadEvidenceCsv}>Evidence CSV</button>
              </div>

              <div className="panel info-panel">
                <div className="panel-header inline-header">
                  <span className="eyebrow">Legal scope</span>
                  <h3>Investigator notice</h3>
                </div>
                <p>{summary.legalNotice}</p>
                {summary.partial ? <div className="error-banner">Partial trace: {summary.partialReasons.join(', ')}. Results are bounded and should not be treated as a complete flow.</div> : null}
                <div className="checksum-box">Evidence checksum: {summary.checksum}</div>
              </div>

              <div className="panel risk-panel">
                <div className="panel-header inline-header">
                  <span className="eyebrow">Risk layers</span>
                  <h3>Multi-layer fraud assessment</h3>
                </div>
                <div className="risk-factors">
                  {(summary.riskFactors.length ? summary.riskFactors : [{name:'Fallback risk',score:summary.probability}]).map((factor:any) => (
                    <div className="risk-pill" key={factor.name}>
                      <span>{factor.name}</span>
                      <strong>{factor.score}</strong>
                    </div>
                  ))}
                </div>
                <div className="suspicious-path-box">
                  <span className="label">Suspicious path</span>
                  <strong>{summary.suspiciousPath.length ? summary.suspiciousPath.join(' ? ') : 'No definitive path found'}</strong>
                </div>
              </div>

              <div className="panel graph-panel">
                <div className="panel-header inline-header">
                  <span className="eyebrow">Flow graph</span>
                  <h3>Wallet relationship graph</h3>
                </div>
                <GraphView data={data} />
              </div>

              <div className="panel evidence-panel">
                <div className="panel-header inline-header">
                  <span className="eyebrow">Evidence</span>
                  <h3>Trace evidence ledger</h3>
                </div>
                <EvidenceTable rows={data.evidence || []} />
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  )
}
