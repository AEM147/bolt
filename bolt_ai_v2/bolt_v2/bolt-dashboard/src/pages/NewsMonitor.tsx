import { useState, useEffect } from 'react'
import { ExternalLink, Clock, TrendingUp, RefreshCw } from 'lucide-react'
import { api } from '../lib/api'

const PILLAR_MAP: Record<string, string> = {
  ai_news:'news', ai_tools:'tools', ai_concepts:'concepts', ai_daily_life:'life',
  '':'news',
}

export default function NewsMonitor() {
  const [articles, setArticles] = useState<any[]>([])
  const [sources,  setSources]  = useState<any[]>([])
  const [loading,  setLoading]  = useState(true)
  const [search,   setSearch]   = useState('')
  const [pillar,   setPillar]   = useState('all')
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    try {
      const [newsData, statusData] = await Promise.all([api.news(), api.status()])
      setArticles(newsData.articles || [])
      // Build sources from status providers + news source list
      const providers = statusData.providers || {}
      const srcList = Object.entries(providers.voice || {}).map(([k,v]:any) => ({
        name: k, status: v.available ? 'ok' : 'off', type:'voice'
      }))
      setSources(srcList)
    } catch {
      // Fallback: show empty state rather than fake data
      setArticles([])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const refresh = async () => {
    setRefreshing(true)
    try { await api.runStep('news') }
    catch {}
    setTimeout(() => { load(); setRefreshing(false) }, 3000)
  }

  const filtered = articles.filter(a => {
    const matchSearch = !search || a.title?.toLowerCase().includes(search.toLowerCase()) || a.source?.toLowerCase().includes(search.toLowerCase())
    const matchPillar = pillar === 'all' || a.pillar === pillar || a.content_pillar === pillar
    return matchSearch && matchPillar
  })

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:16 }}>
      {/* Stats */}
      <div style={{ display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:10 }}>
        {[
          { label:'Articles in DB',  value:String(articles.length),                      sub:'total fetched' },
          { label:'AI-relevant',     value:String(filtered.length),                       sub:'after filter' },
          { label:'Sources active',  value:'17',                                           sub:'RSS feeds' },
          { label:'Status',          value:loading ? '...' : (articles.length?'Live':'Empty'), sub:'data source' },
        ].map(s => (
          <div key={s.label} className="bolt-card" style={{ padding:'14px 16px' }}>
            <div style={{ fontSize:11,color:'var(--bolt-text-dim)',fontWeight:600,textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:6 }}>{s.label}</div>
            <div style={{ fontSize:24,fontWeight:700,color:'var(--bolt-text)',letterSpacing:'-0.03em',lineHeight:1,marginBottom:3 }}>{s.value}</div>
            <div style={{ fontSize:11,color:'var(--bolt-text-muted)' }}>{s.sub}</div>
          </div>
        ))}
      </div>

      <div style={{ display:'grid',gridTemplateColumns:'1fr 240px',gap:16 }}>
        {/* Articles */}
        <div className="bolt-card" style={{ padding:'18px' }}>
          <div style={{ display:'flex',gap:10,marginBottom:16,alignItems:'center',flexWrap:'wrap' }}>
            <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search articles..."
              style={{ flex:1,minWidth:160,padding:'7px 12px',fontSize:13,borderRadius:8,background:'var(--bolt-surface-2)',border:'1px solid var(--bolt-border-bright)',color:'var(--bolt-text)' }} />
            <select value={pillar} onChange={e=>setPillar(e.target.value)}
              style={{ padding:'7px 12px',fontSize:12,borderRadius:8,background:'var(--bolt-surface-2)',border:'1px solid var(--bolt-border-bright)',color:'var(--bolt-text)' }}>
              <option value="all">All pillars</option>
              <option value="ai_news">AI News</option>
              <option value="ai_tools">AI Tools</option>
              <option value="ai_concepts">AI Concepts</option>
              <option value="ai_daily_life">Daily Life</option>
            </select>
            <button className="btn-ghost" onClick={refresh} disabled={refreshing}
              style={{ padding:'7px 12px',display:'flex',alignItems:'center',gap:6,fontSize:12 }}>
              <RefreshCw size={12} /> {refreshing ? 'Fetching...' : 'Run news step'}
            </button>
          </div>

          {loading ? (
            <div style={{ textAlign:'center',color:'var(--bolt-text-muted)',fontSize:13,padding:'30px 0' }}>Loading articles from database...</div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign:'center',color:'var(--bolt-text-muted)',fontSize:13,padding:'30px 0' }}>
              {articles.length === 0
                ? 'No articles in database yet. Click "Run news step" to fetch AI news.'
                : 'No articles match your filters.'}
            </div>
          ) : filtered.map((a:any, i:number) => {
            const score = a.claude_score || a.heuristic_score || 0
            const p = PILLAR_MAP[a.pillar || a.content_pillar || ''] || 'news'
            const age = a.age_hours ? `${Math.round(a.age_hours)}h ago` : (a.fetched_at ? a.fetched_at.slice(0,10) : '')
            return (
              <div key={i} style={{ padding:'12px 0',borderBottom:i<filtered.length-1?'1px solid var(--bolt-border)':'none',display:'flex',gap:12,alignItems:'flex-start' }}>
                <div style={{ flex:1 }}>
                  <div style={{ display:'flex',alignItems:'flex-start',gap:8,marginBottom:6 }}>
                    <div style={{ fontSize:13,fontWeight:600,color:'var(--bolt-text)',lineHeight:1.4,flex:1 }}>{a.title}</div>
                    <span className={`score-badge ${score>=8.5?'score-high':score>=7?'score-mid':'score-low'}`}>{score.toFixed(1)}</span>
                  </div>
                  <div style={{ display:'flex',gap:8,alignItems:'center' }}>
                    <span className={`tag-pill tag-${p}`}>{p.replace('_',' ')}</span>
                    <span style={{ fontSize:11,color:'var(--bolt-text-muted)' }}>{a.source}</span>
                    {age && <div style={{ display:'flex',alignItems:'center',gap:3,fontSize:11,color:'var(--bolt-text-muted)' }}><Clock size={10}/>{age}</div>}
                    <span style={{ fontSize:10,padding:'1px 7px',borderRadius:10,background:a.status==='used'?'rgba(0,229,160,0.1)':'rgba(107,163,255,0.1)',color:a.status==='used'?'var(--bolt-green)':'#6BA3FF' }}>{a.status||'pending'}</span>
                  </div>
                </div>
                {a.link && <a href={a.link} target="_blank" rel="noreferrer" style={{ color:'var(--bolt-text-muted)',display:'flex',marginTop:2 }}><ExternalLink size={13}/></a>}
              </div>
            )
          })}
        </div>

        {/* RSS Sources */}
        <div className="bolt-card" style={{ padding:'16px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:14,display:'flex',alignItems:'center',gap:8 }}>
            <TrendingUp size={14} color="var(--bolt-yellow)"/> Active RSS Sources
          </div>
          {[
            'OpenAI Blog','Anthropic Blog','TechCrunch AI','The Verge AI','MIT Tech Review',
            'WIRED AI','VentureBeat AI','Google DeepMind','Hugging Face','NVIDIA Blog',
            'Ars Technica','ScienceDaily AI','Google AI Blog','Microsoft Research','AI News',
            'KDnuggets','Towards Data Science',
          ].map((src, i) => (
            <div key={src} style={{ display:'flex',alignItems:'center',gap:8,padding:'7px 0',borderBottom:'1px solid var(--bolt-border)' }}>
              <span className="status-dot online" />
              <div style={{ flex:1,minWidth:0 }}>
                <div style={{ fontSize:12,fontWeight:500,color:'var(--bolt-text)',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis' }}>{src}</div>
              </div>
            </div>
          ))}
          <div style={{ marginTop:12,fontSize:11,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace',textAlign:'center' }}>
            17 feeds · 6h refresh cycle
          </div>
        </div>
      </div>
    </div>
  )
}
