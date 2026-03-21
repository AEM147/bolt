import { useState, useEffect } from 'react'
import { DollarSign, HardDrive, Download, RotateCcw, Plus, AlertTriangle } from 'lucide-react'
import { api } from '../lib/api'

function ServiceBar({ label, cost, total, color }: { label:string;cost:number;total:number;color:string }) {
  const pct = total > 0 ? (cost / total) * 100 : 0
  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:'flex',justifyContent:'space-between',marginBottom:4 }}>
        <span style={{ fontSize:12,color:'var(--bolt-text-dim)' }}>{label}</span>
        <div style={{ display:'flex',gap:8 }}>
          <span style={{ fontSize:11,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>{pct.toFixed(0)}%</span>
          <span style={{ fontSize:12,color:'var(--bolt-text)',fontFamily:'JetBrains Mono,monospace',fontWeight:600 }}>${cost.toFixed(4)}</span>
        </div>
      </div>
      <div className="progress-bar" style={{ height:6 }}>
        <div className="progress-fill" style={{ width:`${pct}%`,background:color }} />
      </div>
    </div>
  )
}

function BackupTypeBadge({ type }: { type:string }) {
  const map:Record<string,[string,string]> = {
    daily:   ['rgba(0,229,160,0.12)','var(--bolt-green)'],
    weekly:  ['rgba(107,163,255,0.12)','#6BA3FF'],
    monthly: ['rgba(255,255,0,0.1)','var(--bolt-yellow)'],
    manual:  ['rgba(255,140,66,0.1)','var(--bolt-orange)'],
  }
  const [bg,color] = map[type] || ['rgba(100,100,100,0.1)','var(--bolt-text-dim)']
  return <span style={{ fontSize:10,fontWeight:700,padding:'2px 9px',borderRadius:20,background:bg,color,textTransform:'uppercase',letterSpacing:'0.06em' }}>{type}</span>
}

export default function CostBackups() {
  const [costs, setCosts]   = useState<any>(null)
  const [backups, setBackups] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [backingUp, setBackingUp] = useState(false)

  const load = () => {
    Promise.all([api.costs(), api.backups()])
      .then(([c, b]) => { setCosts(c); setBackups(b.backups || []) })
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleBackup = async () => {
    setBackingUp(true)
    try { await api.createBackup('manual'); setTimeout(load, 2000) }
    finally { setBackingUp(false) }
  }

  if (loading) return <div style={{ color:'var(--bolt-text-muted)',fontSize:13,padding:'40px 0',textAlign:'center' }}>Loading live cost data...</div>

  const monthTotal   = costs?.total_usd || 0
  const allTime      = costs?.all_time  || {}
  const budgetStatus = costs?.budget_status || {}
  const budgetAlerts = budgetStatus?.alerts || []
  const hardStop     = budgetAlerts.some((a:any) => a.type === 'hard_stop')
  const monthlyBudget = budgetStatus?.limits?.monthly_budget_hard_stop || 20
  const budgetPct    = (monthTotal / monthlyBudget) * 100
  const budgetColor  = hardStop ? 'var(--bolt-red)' : budgetPct > 70 ? 'var(--bolt-orange)' : 'var(--bolt-green)'
  const byService    = costs?.by_service || {}

  return (
    <div style={{ display:'flex',flexDirection:'column',gap:18 }}>

      {hardStop && (
        <div style={{ padding:'12px 16px',borderRadius:8,background:'rgba(255,69,96,0.1)',border:'1px solid rgba(255,69,96,0.3)',display:'flex',alignItems:'center',gap:10 }}>
          <AlertTriangle size={16} color="var(--bolt-red)" />
          <div style={{ fontSize:13,color:'var(--bolt-red)',fontWeight:600 }}>
            Budget hard stop active — pipeline is blocked. Update limits in config.json or wait for period reset.
          </div>
        </div>
      )}

      <div style={{ display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:12 }}>
        {[
          { label:'Total spent all time',value:`$${allTime.total_spent?.toFixed(2)||'0.00'}`, accent:'var(--bolt-yellow)' },
          { label:'This month',           value:`$${monthTotal.toFixed(2)}`,                  accent:budgetColor },
          { label:'Avg cost per video',   value:`$${(allTime.avg_cost_per_video||0).toFixed(3)}`, accent:'var(--bolt-green)' },
          { label:'Videos produced',      value:String(allTime.total_videos||0),              accent:'#6BA3FF' },
        ].map(c => (
          <div key={c.label} className="bolt-card" style={{ padding:'16px 18px',position:'relative',overflow:'hidden' }}>
            <div style={{ position:'absolute',left:0,top:0,bottom:0,width:3,background:c.accent,borderRadius:'12px 0 0 12px' }} />
            <div style={{ paddingLeft:8 }}>
              <div style={{ fontSize:11,color:'var(--bolt-text-dim)',fontWeight:600,textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:6 }}>{c.label}</div>
              <div style={{ fontSize:26,fontWeight:700,color:'var(--bolt-text)',letterSpacing:'-0.03em',lineHeight:1 }}>{c.value}</div>
            </div>
          </div>
        ))}
      </div>

      <div style={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:16 }}>
        <div className="bolt-card" style={{ padding:'18px 20px' }}>
          <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',marginBottom:16,display:'flex',alignItems:'center',gap:8 }}>
            <DollarSign size={14} color="var(--bolt-yellow)" /> Monthly budget
          </div>
          <div style={{ marginBottom:12 }}>
            <div style={{ display:'flex',justifyContent:'space-between',marginBottom:6 }}>
              <span style={{ fontSize:12,color:'var(--bolt-text-dim)' }}>${monthTotal.toFixed(2)} of ${monthlyBudget}</span>
              <span style={{ fontSize:12,fontFamily:'JetBrains Mono,monospace',fontWeight:600,color:budgetColor }}>{budgetPct.toFixed(0)}%</span>
            </div>
            <div className="progress-bar" style={{ height:8 }}>
              <div className="progress-fill" style={{ width:`${Math.min(budgetPct,100)}%`,background:budgetColor }} />
            </div>
          </div>
          <div style={{ borderTop:'1px solid var(--bolt-border)',paddingTop:14,marginTop:4 }}>
            <div style={{ fontSize:11,fontWeight:700,color:'var(--bolt-text-dim)',textTransform:'uppercase',letterSpacing:'0.06em',marginBottom:12 }}>Cost by service</div>
            {Object.entries(byService).map(([svc,data]:any) => (
              <ServiceBar key={svc} label={svc} cost={data.total} total={monthTotal}
                color={svc.includes('free')||svc==='edge_tts'||svc==='buffer'?'var(--bolt-green)':'rgba(255,255,0,0.5)'} />
            ))}
            {Object.keys(byService).length === 0 && (
              <div style={{ fontSize:12,color:'var(--bolt-text-muted)' }}>No spending recorded yet. Cost tracking starts after first pipeline run.</div>
            )}
          </div>
          <div style={{ marginTop:12,padding:'8px 12px',borderRadius:6,background:'rgba(0,229,160,0.06)',border:'1px solid rgba(0,229,160,0.14)',fontSize:12,color:'var(--bolt-green)' }}>
            💡 Edge-TTS and Google TTS are free — pipeline uses them as primary voice, saving ~$0.05/video
          </div>
        </div>

        <div className="bolt-card" style={{ padding:'18px 20px' }}>
          <div style={{ display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:16 }}>
            <div style={{ fontSize:13,fontWeight:700,color:'var(--bolt-text)',display:'flex',alignItems:'center',gap:8 }}>
              <HardDrive size={14} color="var(--bolt-yellow)" /> Backups ({backups.length})
            </div>
            <button className="btn-ghost" style={{ padding:'6px 12px',fontSize:12,display:'flex',alignItems:'center',gap:5 }}
              onClick={handleBackup} disabled={backingUp}>
              <Plus size={11} /> {backingUp ? 'Creating...' : 'Manual Backup'}
            </button>
          </div>

          {backups.length === 0 ? (
            <div style={{ fontSize:12,color:'var(--bolt-text-muted)',textAlign:'center',padding:'20px 0' }}>
              No backups yet. Click Manual Backup to create the first one.
            </div>
          ) : backups.slice(0,8).map((b:any,i:number) => (
            <div key={i} style={{ display:'flex',alignItems:'center',gap:10,padding:'8px 0',borderBottom:i<backups.length-1?'1px solid var(--bolt-border)':'none' }}>
              <BackupTypeBadge type={b.type||'manual'} />
              <div style={{ flex:1,fontSize:11,color:'var(--bolt-text-dim)',fontFamily:'JetBrains Mono,monospace',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>
                {String(b.timestamp||'').slice(0,16)}
              </div>
              <div style={{ fontSize:11,color:'var(--bolt-text)',fontFamily:'JetBrains Mono,monospace',fontWeight:600 }}>{b.size_mb} MB</div>
              <button title="Restore" onClick={() => api.restoreBackup(b.id)}
                style={{ background:'transparent',border:'none',cursor:'pointer',color:'var(--bolt-text-muted)',padding:'2px 4px' }}>
                <RotateCcw size={12} />
              </button>
            </div>
          ))}

          <div style={{ marginTop:14,display:'grid',gridTemplateColumns:'repeat(3,1fr)',gap:8 }}>
            {[
              { label:'Daily',   value:'7 kept',  sub:'3 AM UTC',     color:'var(--bolt-green)' },
              { label:'Weekly',  value:'4 kept',  sub:'Mon 2 AM UTC', color:'#6BA3FF' },
              { label:'Monthly', value:'12 kept', sub:'1st of month', color:'var(--bolt-yellow)' },
            ].map(s => (
              <div key={s.label} style={{ padding:'8px 10px',borderRadius:8,background:'var(--bolt-surface-2)',border:'1px solid var(--bolt-border)' }}>
                <div style={{ fontSize:10,color:'var(--bolt-text-muted)',marginBottom:2 }}>{s.label}</div>
                <div style={{ fontSize:13,fontWeight:700,color:s.color,marginBottom:1 }}>{s.value}</div>
                <div style={{ fontSize:10,color:'var(--bolt-text-muted)',fontFamily:'JetBrains Mono,monospace' }}>{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
