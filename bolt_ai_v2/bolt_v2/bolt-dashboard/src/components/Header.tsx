import { useEffect, useState } from 'react'
import { RefreshCw, Zap, Circle } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { api } from '../lib/api'

const TITLES: Record<string,string> = {
  '/':'Overview','/content':'Content Queue','/analytics':'Analytics',
  '/news':'News Monitor','/platforms':'Platforms','/costs':'Cost & Backups','/settings':'Settings',
}

interface LiveStatus {
  pipeline_running: boolean
  pending_review:   number
  failed_jobs:      number
  hitl_waiting:     number
  month_cost:       number
}

export default function Header() {
  const location  = useLocation()
  const title     = TITLES[location.pathname] || 'Dashboard'
  const [live, setLive]   = useState<LiveStatus|null>(null)
  const [connected, setConnected] = useState(false)
  const [running, setRunning]   = useState(false)

  useEffect(() => {
    // Connect to SSE stream for real-time updates
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000'
    const es = new EventSource(`${apiBase}/api/stream/status`)
    es.onopen    = ()  => setConnected(true)
    es.onerror   = ()  => setConnected(false)
    es.onmessage = (e) => {
      try { setLive(JSON.parse(e.data)); setConnected(true) }
      catch {}
    }
    return () => es.close()
  }, [])

  const triggerPipeline = async () => {
    setRunning(true)
    try { await api.runPipeline() }
    catch {}
    setTimeout(() => setRunning(false), 3000)
  }

  const now = new Date().toLocaleString('en-US', {weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})

  return (
    <div style={{ height:56,display:'flex',alignItems:'center',justifyContent:'space-between',padding:'0 24px',borderBottom:'1px solid var(--bolt-border)',background:'var(--bolt-surface)',position:'sticky',top:0,zIndex:10 }}>
      <div style={{ display:'flex',alignItems:'center',gap:12 }}>
        <h1 style={{ fontSize:16,fontWeight:700,color:'var(--bolt-text)',margin:0,letterSpacing:'-0.02em' }}>{title}</h1>
        <span style={{ fontSize:11,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>{now}</span>

        {/* Live connection indicator */}
        <div style={{ display:'flex',alignItems:'center',gap:5,padding:'3px 10px',borderRadius:20,background:connected?'rgba(0,229,160,0.08)':'rgba(100,100,100,0.08)',border:`1px solid ${connected?'rgba(0,229,160,0.2)':'var(--bolt-border)'}` }}>
          <span className={`status-dot ${connected?'online':'offline'}`} style={{ width:6,height:6 }} />
          <span style={{ fontSize:10,fontWeight:600,color:connected?'var(--bolt-green)':'var(--bolt-text-muted)' }}>
            {connected ? 'Live' : 'Offline'}
          </span>
        </div>

        {/* Real-time alerts from SSE */}
        {live && live.hitl_waiting > 0 && (
          <div style={{ padding:'3px 10px',borderRadius:20,background:'rgba(255,170,0,0.1)',border:'1px solid rgba(255,170,0,0.25)',fontSize:10,fontWeight:700,color:'var(--bolt-orange)' }}>
            👁️ {live.hitl_waiting} awaiting review
          </div>
        )}
        {live && live.failed_jobs > 0 && (
          <div style={{ padding:'3px 10px',borderRadius:20,background:'rgba(255,69,96,0.1)',border:'1px solid rgba(255,69,96,0.25)',fontSize:10,fontWeight:700,color:'var(--bolt-red)' }}>
            ⚠️ {live.failed_jobs} failed jobs
          </div>
        )}
        {live && live.pipeline_running && (
          <div style={{ padding:'3px 10px',borderRadius:20,background:'rgba(255,255,0,0.1)',border:'1px solid rgba(255,255,0,0.25)',fontSize:10,fontWeight:700,color:'var(--bolt-yellow)' }}>
            ⚡ Pipeline running
          </div>
        )}
      </div>

      <div style={{ display:'flex',alignItems:'center',gap:8 }}>
        {/* Live cost display */}
        {live && (
          <div style={{ fontSize:11,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace',padding:'4px 10px',borderRadius:6,background:'var(--bolt-surface-2)' }}>
            ${live.month_cost.toFixed(3)}<span style={{ color:'var(--bolt-text-muted)',fontSize:10 }}>/mo</span>
          </div>
        )}
        <button className="btn-ghost" style={{ padding:'6px 10px',display:'flex',alignItems:'center',gap:6 }} onClick={() => window.location.reload()}>
          <RefreshCw size={13}/> Refresh
        </button>
        <button className="btn-yellow" onClick={triggerPipeline} disabled={running}
          style={{ padding:'6px 14px',display:'flex',alignItems:'center',gap:6 }}>
          <Zap size={13}/> {running ? 'Starting...' : 'Run Pipeline'}
        </button>
      </div>
    </div>
  )
}
