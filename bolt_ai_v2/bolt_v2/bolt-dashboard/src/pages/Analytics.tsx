import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid } from 'recharts'
import { api } from '../lib/api'

const fmt = (n: number) => n >= 1_000_000 ? `${(n/1_000_000).toFixed(1)}M` : n >= 1_000 ? `${(n/1_000).toFixed(0)}K` : String(n)

function Stat({ label, value, change, color }: { label:string; value:string; change?:string; color?:string }) {
  return (
    <div className="bolt-card" style={{ padding:'16px 18px' }}>
      <div style={{ fontSize:11,color:'var(--bolt-text-dim)',fontWeight:600,textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:6 }}>{label}</div>
      <div style={{ fontSize:26,fontWeight:700,color:color||'var(--bolt-text)',letterSpacing:'-0.03em',lineHeight:1,marginBottom:4 }}>{value}</div>
      {change && <div style={{ fontSize:12,color:'var(--bolt-green)' }}>↑ {change} vs last period</div>}
    </div>
  )
}

export default function Analytics() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.analytics()
      .then(setData)
      .catch(() => {
        // Fallback to static file
        fetch('/data/analytics.json').then(r=>r.json()).then(setData).catch(()=>{})
      })
      .finally(() => setLoading(false))
  }, [])

  const s = data?.summary || {}
  const yt = data?.platforms?.youtube || {}
  const tt = data?.platforms?.tiktok  || {}
  const ig = data?.platforms?.instagram || {}

  // Build monthly chart from whatever data we have
  const monthly = data?.weekly_views || [
    {day:'Mon',youtube:yt.recent_30_views?Math.floor(yt.recent_30_views/30):0,tiktok:tt.recent_20_views?Math.floor(tt.recent_20_views/7):0,instagram:ig.recent_20_plays?Math.floor(ig.recent_20_plays/7):0},
  ]

  if (loading) return (
    <div style={{ display:'flex',alignItems:'center',justifyContent:'center',height:200,color:'var(--bolt-text-dim)',fontSize:13 }}>
      Loading live analytics...
    </div>
  )

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:18 }}>
      <div style={{ fontSize:12,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>
        Live data from DB · Updated daily at 09:00 UTC · {data?.generated_at?.slice(0,16).replace('T',' ')} UTC
      </div>

      <div style={{ display:'grid',gridTemplateColumns:'repeat(5,1fr)',gap:10 }}>
        <Stat label="Total Views (30d)" value={fmt(s.total_views_30d||0)} />
        <Stat label="YT Subscribers"   value={fmt(yt.subscribers||0)}     color="#FF4040" />
        <Stat label="TikTok Followers" value={fmt(tt.followers||0)}        color="#00F2EA" />
        <Stat label="IG Followers"     value={fmt(ig.followers||0)}        color="#E1306C" />
        <Stat label="Avg Engagement"   value={`${s.avg_engagement_rate||0}%`} color="var(--bolt-green)" />
      </div>

      <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:16 }}>
        <div className="bolt-card" style={{ padding:'18px 18px 10px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:16 }}>Views trend</div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={monthly} barCategoryGap="30%">
              <XAxis dataKey="day" tick={{ fill:'#7A8AA0',fontSize:11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill:'#7A8AA0',fontSize:10 }} axisLine={false} tickLine={false} tickFormatter={fmt} />
              <Tooltip contentStyle={{ background:'#121C2E',border:'1px solid rgba(255,255,255,0.1)',borderRadius:8,color:'#E8EDF5',fontSize:12 }} formatter={fmt} />
              <Bar dataKey="youtube"   fill="#FF4040" radius={[3,3,0,0]} />
              <Bar dataKey="tiktok"    fill="#00F2EA" radius={[3,3,0,0]} />
              <Bar dataKey="instagram" fill="#E1306C" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="bolt-card" style={{ padding:'18px 18px 10px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:4 }}>Platform breakdown</div>
          <div style={{ fontSize:12,color:'var(--bolt-text-dim)',marginBottom:14 }}>Videos published per platform</div>
          <div style={{ display:'flex',flexDirection:'column',gap:14,marginTop:24 }}>
            {[
              { name:'YouTube',   val: fmt(yt.subscribers||0),     sub:`${fmt(yt.recent_30_views||0)} views`, color:'#FF4040' },
              { name:'TikTok',    val: fmt(tt.followers||0),        sub:`${fmt(tt.recent_20_views||0)} views`, color:'#00F2EA' },
              { name:'Instagram', val: fmt(ig.followers||0),        sub:`${fmt(ig.recent_20_plays||0)} plays`, color:'#E1306C' },
            ].map(p => (
              <div key={p.name} style={{ display:'flex',alignItems:'center',justifyContent:'space-between' }}>
                <div style={{ display:'flex',alignItems:'center',gap:8 }}>
                  <div style={{ width:8,height:8,borderRadius:2,background:p.color,flexShrink:0 }}/>
                  <div>
                    <div style={{ fontSize:13,fontWeight:500,color:'var(--bolt-text)' }}>{p.name}</div>
                    <div style={{ fontSize:11,color:'var(--bolt-text-muted)' }}>{p.sub}</div>
                  </div>
                </div>
                <div style={{ fontSize:16,fontWeight:700,color:p.color,fontFamily:'JetBrains Mono,monospace' }}>{p.val}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bolt-card" style={{ padding:'18px 20px' }}>
        <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:16 }}>Recent published content</div>
        {(data?.recent_content||[]).length === 0 ? (
          <div style={{ fontSize:13,color:'var(--bolt-text-muted)',textAlign:'center',padding:'20px 0' }}>
            No published content yet. Content will appear here after the first successful pipeline run.
          </div>
        ) : (data?.recent_content||[]).map((item:any,i:number) => (
          <div key={i} style={{ display:'flex',alignItems:'center',gap:14,padding:'10px 0',borderBottom:i<(data?.recent_content?.length-1)?'1px solid var(--bolt-border)':'none' }}>
            <div style={{ fontSize:13,fontWeight:500,color:'var(--bolt-text)',flex:1 }}>{item.title||item.script?.slice(0,60)||'—'}</div>
            <div style={{ fontSize:11,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>{item.generated_at?.slice(0,10)||''}</div>
            <span className={`score-badge ${(item.overall_score||0)>=8.5?'score-high':'score-mid'}`}>{(item.overall_score||0).toFixed(1)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
