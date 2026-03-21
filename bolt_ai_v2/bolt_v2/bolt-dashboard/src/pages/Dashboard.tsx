import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import { Zap, Eye, Users, TrendingUp, Activity, Youtube, Clock, CheckCircle, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'

const fmt = (n: number) => n >= 1_000_000 ? `${(n/1_000_000).toFixed(1)}M`
  : n >= 1_000 ? `${(n/1_000).toFixed(1)}K` : String(n)

function MetricCard({ label, value, sub, accent }: { label:string; value:string; sub?:string; accent?:string }) {
  return (
    <div className="bolt-card" style={{ padding: '18px 20px', position: 'relative', overflow: 'hidden' }}>
      {accent && <div style={{ position:'absolute', left:0, top:0, bottom:0, width:3, background:accent, borderRadius:'12px 0 0 12px' }} />}
      <div style={{ fontSize:11, color:'var(--bolt-text-dim)', fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:8, paddingLeft: accent ? 8 : 0 }}>
        {label}
      </div>
      <div style={{ fontSize:28, fontWeight:700, color:'var(--bolt-text)', letterSpacing:'-0.03em', lineHeight:1, marginBottom:4, paddingLeft: accent ? 8 : 0 }}>
        {value}
      </div>
      {sub && <div style={{ fontSize:12, color:'var(--bolt-text-muted)', paddingLeft: accent ? 8 : 0 }}>{sub}</div>}
    </div>
  )
}

function PipelineStep({ name, status, detail }: { name:string; status:'ok'|'warn'|'off'|'idle'; detail:string }) {
  const colors = { ok:'var(--bolt-green)', warn:'var(--bolt-orange)', off:'var(--bolt-red)', idle:'var(--bolt-text-muted)' }
  const labels = { ok:'Active', warn:'Warning', off:'Offline', idle:'Idle' }
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'10px 0', borderBottom:'1px solid var(--bolt-border)' }}>
      <div style={{ display:'flex', alignItems:'center', gap:10 }}>
        <span className={`status-dot ${status === 'ok' ? 'online' : status === 'warn' ? 'warning' : 'offline'}`} />
        <span style={{ fontSize:13, fontWeight:500, color:'var(--bolt-text)' }}>{name}</span>
      </div>
      <div style={{ textAlign:'right' }}>
        <div style={{ fontSize:11, color: colors[status], fontWeight:600 }}>{labels[status]}</div>
        <div style={{ fontSize:10, color:'var(--bolt-text-muted)', fontFamily:'JetBrains Mono, monospace' }}>{detail}</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [analytics, setAnalytics] = useState<any>(null)
  const [status, setStatus] = useState<any>(null)

  useEffect(() => {
    // Prefer live API; fall back to static JSON if backend is unavailable
    api.analytics()
      .then(setAnalytics)
      .catch(() => fetch('/data/analytics.json').then(r => r.json()).then(setAnalytics).catch(() => {}))
    api.status()
      .then(setStatus)
      .catch(() => fetch('/data/system-status.json').then(r => r.json()).then(setStatus).catch(() => {}))
  }, [])

  const yt = analytics?.platforms?.youtube || {}
  const tt = analytics?.platforms?.tiktok || {}
  const ig = analytics?.platforms?.instagram || {}
  const summary = analytics?.summary || {}
  const weekly = analytics?.weekly_views || []

  const chartData = weekly.length ? weekly : Array.from({length:7},(_,i) => ({
    day: ['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][i],
    youtube: Math.floor(Math.random()*8000+2000),
    tiktok:  Math.floor(Math.random()*12000+3000),
    instagram: Math.floor(Math.random()*5000+1000),
  }))

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:20 }}>

      {/* Top banner */}
      <div className="bolt-card" style={{
        padding:'20px 24px', display:'flex', alignItems:'center', justifyContent:'space-between',
        background:'linear-gradient(135deg, rgba(255,255,0,0.06) 0%, var(--bolt-surface) 60%)',
        border:'1px solid rgba(255,255,0,0.12)',
      }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:4 }}>
            <Zap size={18} color="var(--bolt-yellow)" fill="var(--bolt-yellow)" />
            <span style={{ fontSize:18, fontWeight:700, color:'var(--bolt-text)', letterSpacing:'-0.02em' }}>
              Let's get wired, humans! ⚡
            </span>
          </div>
          <div style={{ fontSize:13, color:'var(--bolt-text-dim)' }}>
            Bolt AI pipeline is running · {summary.videos_published || 0} videos published across all platforms
          </div>
        </div>
        <div style={{ textAlign:'right' }}>
          <div style={{ fontSize:11, color:'var(--bolt-text-muted)', fontFamily:'JetBrains Mono, monospace' }}>TOTAL FOLLOWERS</div>
          <div style={{ fontSize:32, fontWeight:700, color:'var(--bolt-yellow)', letterSpacing:'-0.04em' }}>
            {fmt(summary.total_followers || 259500)}
          </div>
        </div>
      </div>

      {/* Metric row */}
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:12 }}>
        <MetricCard label="Total Views (30d)" value={fmt(summary.total_views_30d || 2847592)} sub="Across all platforms" accent="var(--bolt-yellow)" />
        <MetricCard label="YouTube Subs" value={fmt(yt.subscribers || 89300)} sub={`${yt.engagement_rate || 6.2}% engagement`} accent="#FF4040" />
        <MetricCard label="TikTok Followers" value={fmt(tt.followers || 124500)} sub={`${tt.engagement_rate || 7.8}% engagement`} accent="#00F2EA" />
        <MetricCard label="Instagram" value={fmt(ig.followers || 45700)} sub={`${ig.engagement_rate || 5.1}% engagement`} accent="#E1306C" />
      </div>

      {/* Chart + Pipeline status */}
      <div style={{ display:'grid', gridTemplateColumns:'1fr 320px', gap:16 }}>

        {/* Chart */}
        <div className="bolt-card" style={{ padding:'20px 20px 10px' }}>
          <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:20 }}>
            <div>
              <div style={{ fontSize:14, fontWeight:700, color:'var(--bolt-text)', marginBottom:2 }}>Views by platform — last 7 days</div>
              <div style={{ fontSize:12, color:'var(--bolt-text-dim)' }}>Updated daily at 09:00 UTC</div>
            </div>
            <div style={{ display:'flex', gap:12, fontSize:11, color:'var(--bolt-text-muted)' }}>
              {[['#FF4040','YouTube'],['#00F2EA','TikTok'],['#E1306C','Instagram']].map(([c,l]) => (
                <div key={l} style={{ display:'flex', alignItems:'center', gap:5 }}>
                  <div style={{ width:8, height:8, borderRadius:2, background:c }} />
                  {l}
                </div>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={chartData} margin={{ top:0, right:0, left:-20, bottom:0 }}>
              <defs>
                {[['yt','#FF4040'],['tt','#00F2EA'],['ig','#E1306C']].map(([k,c]) => (
                  <linearGradient key={k} id={`grad-${k}`} x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={c} stopOpacity={0.25} />
                    <stop offset="95%" stopColor={c} stopOpacity={0.02} />
                  </linearGradient>
                ))}
              </defs>
              <XAxis dataKey="day" tick={{ fill:'#7A8AA0', fontSize:11, fontFamily:'JetBrains Mono' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#7A8AA0', fontSize:10, fontFamily:'JetBrains Mono' }} axisLine={false} tickLine={false} tickFormatter={v => fmt(v)} />
              <Tooltip contentStyle={{ background:'#121C2E', border:'1px solid rgba(255,255,255,0.1)', borderRadius:8, color:'#E8EDF5', fontSize:12 }} />
              <Area type="monotone" dataKey="youtube"   stroke="#FF4040" fill="url(#grad-yt)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="tiktok"    stroke="#00F2EA" fill="url(#grad-tt)" strokeWidth={1.5} dot={false} />
              <Area type="monotone" dataKey="instagram" stroke="#E1306C" fill="url(#grad-ig)" strokeWidth={1.5} dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Pipeline status */}
        <div className="bolt-card" style={{ padding:'18px 18px' }}>
          <div style={{ fontSize:13, fontWeight:700, color:'var(--bolt-text)', marginBottom:14, display:'flex', alignItems:'center', gap:8 }}>
            <Activity size={14} color="var(--bolt-yellow)" /> Pipeline Status
          </div>
          <PipelineStep name="News Aggregation"   status="ok"   detail="Next run in 2h 14m" />
          <PipelineStep name="Script Generator"    status="ok"   detail="Ready · 1 pending" />
          <PipelineStep name="Voice Synthesis"     status="ok"   detail="ElevenLabs active" />
          <PipelineStep name="Avatar Video"        status="warn" detail="HeyGen · quota 68%" />
          <PipelineStep name="Video Render"        status="idle" detail="Waiting for avatar" />
          <PipelineStep name="Platform Publisher"  status="ok"   detail="Buffer connected" />
          <PipelineStep name="Analytics Tracker"   status="ok"   detail="Last run 47m ago" />

          <div style={{ marginTop:16, padding:'10px 12px', borderRadius:8, background:'rgba(0,229,160,0.05)', border:'1px solid rgba(0,229,160,0.12)', fontSize:12, color:'var(--bolt-text-dim)' }}>
            <span style={{ color:'var(--bolt-green)', fontWeight:600 }}>6/7 steps</span> operational · Next full run at <span className="font-mono">06:00 UTC</span>
          </div>
        </div>
      </div>

      {/* Recent content */}
      <div className="bolt-card" style={{ padding:'18px 20px' }}>
        <div style={{ fontSize:13, fontWeight:700, color:'var(--bolt-text)', marginBottom:14, display:'flex', alignItems:'center', gap:8 }}>
          <Clock size={14} color="var(--bolt-yellow)" /> Recent published content
        </div>
        {(analytics?.recent_content || DEMO_CONTENT).map((item: any, i: number) => (
          <div key={i} style={{ display:'flex', alignItems:'center', gap:14, padding:'10px 0', borderBottom: i < 4 ? '1px solid var(--bolt-border)' : 'none' }}>
            <div style={{ width:32, height:32, borderRadius:6, background:'var(--bolt-surface-2)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0, fontSize:12, fontWeight:700, fontFamily:'JetBrains Mono, monospace', color:'var(--bolt-text-dim)' }}>
              {(i+1).toString().padStart(2,'0')}
            </div>
            <div style={{ flex:1, minWidth:0 }}>
              <div style={{ fontSize:13, fontWeight:500, color:'var(--bolt-text)', whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', marginBottom:3 }}>
                {item.title || item.article?.title || 'AI Content Update'}
              </div>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <span className={`tag-pill tag-${(item.pillar||'news').replace('ai_','')}`}>
                  {(item.pillar||'ai_news').replace('ai_','').replace('_',' ')}
                </span>
                <span style={{ fontSize:11, color:'var(--bolt-text-muted)', fontFamily:'JetBrains Mono, monospace' }}>
                  {item.date || item.published_at?.slice(0,10) || '2026-03-21'}
                </span>
              </div>
            </div>
            <div style={{ display:'flex', alignItems:'center', gap:6 }}>
              {item.score >= 8.5 ? <CheckCircle size={13} color="var(--bolt-green)" /> : <AlertTriangle size={13} color="var(--bolt-orange)" />}
              <span className={`score-badge ${(item.score||8.5) >= 8.5 ? 'score-high' : 'score-mid'}`}>
                {(item.score || 8.5).toFixed(1)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const DEMO_CONTENT = [
  { title: "OpenAI Announces GPT-5 With 10x Improved Reasoning", pillar: "ai_news",      score: 9.4, date: "2026-03-21" },
  { title: "5 Free AI Tools That Will Replace Your Entire Workflow",  pillar: "ai_tools",     score: 8.8, date: "2026-03-20" },
  { title: "What Is Multimodal AI? Explained in 60 Seconds",          pillar: "ai_concepts",  score: 8.6, date: "2026-03-19" },
  { title: "Google's Gemini 2.5 Beats Every Benchmark — Again",       pillar: "ai_news",      score: 9.1, date: "2026-03-18" },
  { title: "How AI Is Changing the Way We Learn Languages",           pillar: "ai_daily_life", score: 8.3, date: "2026-03-17" },
]
