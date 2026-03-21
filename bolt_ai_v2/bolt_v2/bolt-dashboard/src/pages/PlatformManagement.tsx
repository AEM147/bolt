import { useEffect, useState } from 'react'
import { ExternalLink, Zap, TrendingUp, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

function ApiQuota({ label, pct, color }: { label:string;pct:number;color:string }) {
  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:'flex',justifyContent:'space-between',marginBottom:4 }}>
        <span style={{ fontSize:12,color:'var(--bolt-text-dim)' }}>{label}</span>
        <span style={{ fontSize:12,fontFamily:'JetBrains Mono,monospace',fontWeight:600,color:pct>85?'var(--bolt-red)':pct>65?'var(--bolt-orange)':'var(--bolt-green)' }}>{pct}%</span>
      </div>
      <div className="progress-bar" style={{ height:4 }}>
        <div className="progress-fill" style={{ width:`${pct}%`,background:pct>85?'var(--bolt-red)':pct>65?'var(--bolt-orange)':'var(--bolt-green)' }} />
      </div>
    </div>
  )
}

const PLATFORM_META: Record<string,{color:string;icon:string;cls:string}> = {
  youtube:   { color:'#FF4040', icon:'▶', cls:'yt' },
  tiktok:    { color:'#00F2EA', icon:'♪', cls:'tt' },
  instagram: { color:'#E1306C', icon:'◎', cls:'ig' },
}

export default function PlatformManagement() {
  const [status, setStatus]     = useState<any>(null)
  const [analytics, setAnalytics] = useState<any>(null)
  const [scripts, setScripts]   = useState<any[]>([])
  const [jobs, setJobs]         = useState<any>({})
  const [loading, setLoading]   = useState(true)
  const [running, setRunning]   = useState<string|null>(null)

  const load = async () => {
    try {
      const [st, an, sc, jb] = await Promise.all([
        api.status(), api.analytics(), api.scripts('published'), api.jobs()
      ])
      setStatus(st); setAnalytics(an)
      setScripts(sc.scripts || []); setJobs(jb)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const triggerPublish = async () => {
    setRunning('publish')
    try { await api.runStep('publish') }
    catch {}
    setTimeout(() => { load(); setRunning(null) }, 3000)
  }

  const fmt = (n:number) => n>=1_000_000?`${(n/1_000_000).toFixed(1)}M`:n>=1_000?`${(n/1_000).toFixed(1)}K`:String(n||0)

  const providers = status?.providers || {}
  const publishProviders = providers.publish || {}
  const platforms = ['youtube','tiktok','instagram'].map(p => {
    const meta = PLATFORM_META[p]
    const an   = analytics?.platforms?.[p] || {}
    const connected = publishProviders[p]?.available || false
    const byPlat = analytics?.summary?.by_platform || {}
    return {
      id: p, name: p.charAt(0).toUpperCase()+p.slice(1),
      color: meta.color, icon: meta.icon, cls: meta.cls,
      connected,
      followers: fmt(an.followers || an.subscribers || 0),
      views:     fmt(an.recent_30_views || an.recent_20_views || an.recent_20_plays || 0),
      videos:    String(byPlat[p] || 0),
      engagement:`${an.engagement_rate || 0}%`,
    }
  })

  const scheduled = scripts.slice(0,3).map((s:any) => ({
    platform: 'Multi',
    time: s.generated_at?.slice(11,16) || '',
    title: s.script?.slice(0,40) || 'Bolt content',
    status: 'published',
    content_id: s.content_id,
  }))

  if (loading) return (
    <div style={{ color:'var(--bolt-text-muted)',fontSize:13,padding:'40px 0',textAlign:'center' }}>
      Loading platform data...
    </div>
  )

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:16 }}>
      {/* Platform cards */}
      <div style={{ display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:14 }}>
        {platforms.map(p => (
          <div key={p.id} className="bolt-card" style={{ padding:'18px',position:'relative',overflow:'hidden' }}>
            <div style={{ position:'absolute',left:0,top:0,bottom:0,width:3,background:p.color,borderRadius:'12px 0 0 12px' }} />
            <div style={{ paddingLeft:8 }}>
              <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14 }}>
                <div style={{ display:'flex',alignItems:'center',gap:8 }}>
                  <div style={{ width:32,height:32,borderRadius:8,background:`${p.color}18`,display:'flex',alignItems:'center',justifyContent:'center',fontSize:14,color:p.color,fontWeight:700 }}>{p.icon}</div>
                  <div>
                    <div style={{ fontSize:14,fontWeight:700,color:'var(--bolt-text)' }}>{p.name}</div>
                    <div style={{ display:'flex',alignItems:'center',gap:5 }}>
                      <span className={`status-dot ${p.connected?'online':'offline'}`} />
                      <span style={{ fontSize:11,color:p.connected?'var(--bolt-green)':'var(--bolt-red)',fontWeight:600 }}>
                        {p.connected ? 'Connected' : 'Not configured'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:8,marginBottom:14 }}>
                {[
                  { l:'Followers', v:p.followers, c:p.color },
                  { l:'Views',     v:p.views,     c:'var(--bolt-text)' },
                  { l:'Published', v:p.videos,    c:'var(--bolt-text)' },
                ].map(s => (
                  <div key={s.l} style={{ textAlign:'center' }}>
                    <div style={{ fontSize:15,fontWeight:700,color:s.c,fontFamily:'JetBrains Mono,monospace',letterSpacing:'-0.02em' }}>{s.v}</div>
                    <div style={{ fontSize:10,color:'var(--bolt-text-muted)' }}>{s.l}</div>
                  </div>
                ))}
              </div>
              {!p.connected && (
                <div style={{ padding:'8px 10px',borderRadius:6,background:'rgba(255,69,96,0.06)',border:'1px solid rgba(255,69,96,0.18)',fontSize:11,color:'var(--bolt-red)' }}>
                  Add {p.name.toUpperCase()}_ACCESS_TOKEN to .env to connect
                </div>
              )}
              {p.connected && (
                <div style={{ padding:'8px 10px',borderRadius:6,background:'rgba(0,229,160,0.05)',border:'1px solid rgba(0,229,160,0.14)',fontSize:11,color:'var(--bolt-green)' }}>
                  Ready to publish via Buffer or direct API
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:16 }}>
        {/* Job queue status */}
        <div className="bolt-card" style={{ padding:'18px 20px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:14,display:'flex',alignItems:'center',gap:8 }}>
            <Zap size={14} color="var(--bolt-yellow)"/> Job Queue
          </div>
          {Object.keys(jobs.by_status||{}).length === 0 ? (
            <div style={{ fontSize:12,color:'var(--bolt-text-muted)',textAlign:'center',padding:'20px 0' }}>Queue is empty — all jobs completed</div>
          ) : Object.entries(jobs.by_status||{}).map(([status,count]:any) => {
            const icon:Record<string,string> = {pending:'⏳',running:'🔄',retrying:'♻️',done:'✅',dead:'💀'}
            return (
              <div key={status} style={{ display:'flex',justifyContent:'space-between',padding:'8px 0',borderBottom:'1px solid var(--bolt-border)',alignItems:'center' }}>
                <span style={{ fontSize:13,color:'var(--bolt-text)' }}>{icon[status]||'·'} {status}</span>
                <span style={{ fontSize:13,fontFamily:'JetBrains Mono,monospace',fontWeight:600,color:'var(--bolt-text)' }}>{count}</span>
              </div>
            )
          })}
          <button className="btn-yellow" onClick={triggerPublish} disabled={running==='publish'}
            style={{ marginTop:14,width:'100%',display:'flex',alignItems:'center',justifyContent:'center',gap:6 }}>
            {running==='publish' ? '⏳ Publishing...' : '🚀 Publish Now'}
          </button>
        </div>

        {/* Recent published */}
        <div className="bolt-card" style={{ padding:'18px 20px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:14,display:'flex',alignItems:'center',gap:8 }}>
            <TrendingUp size={14} color="var(--bolt-yellow)"/> Recent Publishes
          </div>
          {scripts.length === 0 ? (
            <div style={{ fontSize:12,color:'var(--bolt-text-muted)',textAlign:'center',padding:'20px 0' }}>No published content yet</div>
          ) : scripts.slice(0,5).map((s:any,i:number) => (
            <div key={i} style={{ padding:'9px 0',borderBottom:i<4?'1px solid var(--bolt-border)':'none' }}>
              <div style={{ fontSize:12,fontWeight:500,color:'var(--bolt-text)',marginBottom:3,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>
                {s.script?.slice(0,55)||'—'}...
              </div>
              <div style={{ display:'flex',gap:8,alignItems:'center' }}>
                <span className={`tag-pill tag-${(s.pillar||'ai_news').replace('ai_','')}`}>{(s.pillar||'ai_news').replace('ai_','').replace('_',' ')}</span>
                <span style={{ fontSize:10,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>{s.generated_at?.slice(0,10)||''}</span>
                <span className="score-badge score-high">{(s.overall_score||0).toFixed(1)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
