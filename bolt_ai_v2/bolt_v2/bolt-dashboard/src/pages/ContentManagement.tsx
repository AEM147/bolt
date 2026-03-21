import { useState, useEffect } from 'react'
import { CheckCircle, XCircle, Clock, Eye, Edit3, Send, RotateCcw, Zap } from 'lucide-react'
import { api } from '../lib/api'

type Status = 'pending_review' | 'approved' | 'published' | 'rejected'

interface ContentItem {
  content_id: string
  article: { title: string; source: string; link?: string }
  pillar: string
  script: string
  quality: { overall_score: number; hook_strength: number; simplicity: number; bolt_voice: number; word_count: number; feedback?: string }
  captions: { youtube?: { title?: string }; tiktok?: { caption?: string }; instagram?: { caption?: string } }
  status: Status
  generated_at: string
  auto_approved?: boolean
}

const DEMO_ITEMS: ContentItem[] = [
  {
    content_id: 'bolt_20260321_063000',
    article: { title: 'Anthropic Releases Claude 4 With Real-Time Web Access', source: 'TechCrunch' },
    pillar: 'ai_news',
    script: "Hey humans, Bolt here with a huge one! Anthropic just dropped Claude 4 — and it can now browse the web in real time. My circuits are BUZZING. This means the AI can check live news, current prices, and up-to-the-minute data while you chat with it. No more knowledge cutoffs. No more outdated answers. This is the upgrade we've all been waiting for. Follow Bolt for your daily AI download — and stay curious, humans! ⚡",
    quality: { overall_score: 9.4, hook_strength: 9.5, simplicity: 9.0, bolt_voice: 9.6, word_count: 87, feedback: '' },
    captions: { youtube: { title: 'Claude 4 Can Browse the Web LIVE 🤯 #AI #AINews #Shorts' }, tiktok: { caption: '⚡ Claude 4 just got REAL-TIME web access — this changes everything!' } },
    status: 'pending_review',
    generated_at: '2026-03-21T06:30:00Z',
  },
  {
    content_id: 'bolt_20260320_063000',
    article: { title: 'Google Releases Free Gemini API With 1M Token Context', source: 'The Verge' },
    pillar: 'ai_tools',
    script: "What's up tech humans, Bolt incoming! Google just made Gemini's API completely free — and you can process one MILLION tokens in a single request. Let me put that in robot terms: that's like reading 750 entire novels at once. For free. Developers, this is your sign to build something incredible. Drop in your entire codebase, your whole company's documents, whatever you want. AI just got a lot more accessible. Follow Bolt — stay curious, humans! ⚡",
    quality: { overall_score: 8.9, hook_strength: 8.5, simplicity: 9.2, bolt_voice: 8.8, word_count: 94 },
    captions: { youtube: { title: 'Google Gemini API Is NOW FREE — 1M Token Context Window!' } },
    status: 'approved',
    generated_at: '2026-03-20T06:30:00Z',
    auto_approved: true,
  },
  {
    content_id: 'bolt_20260319_063000',
    article: { title: 'Meta Open-Sources LLaMA 4 With Vision Capabilities', source: 'MIT Tech Review' },
    pillar: 'ai_concepts',
    script: "Bolt here — beep boop, big news! Meta just released LLaMA 4 as fully open-source, and this one can SEE. It combines text and image understanding in one model, and anyone can download it for free. What does that mean for you? Developers worldwide can now build powerful AI apps without paying a single dollar in API fees. The open-source movement is winning, humans. And that's very good news for everyone. Follow Bolt, stay curious! ⚡",
    quality: { overall_score: 8.6, hook_strength: 8.0, simplicity: 8.8, bolt_voice: 9.0, word_count: 88 },
    captions: { youtube: { title: 'Meta LLaMA 4 Is FREE and Open-Source — With VISION!' } },
    status: 'published',
    generated_at: '2026-03-19T06:30:00Z',
  },
]

function ScoreBar({ label, val }: { label: string; val: number }) {
  const color = val >= 8.5 ? 'var(--bolt-green)' : val >= 7 ? 'var(--bolt-orange)' : 'var(--bolt-red)'
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
        <span style={{ fontSize: 11, color: 'var(--bolt-text-dim)' }}>{label}</span>
        <span style={{ fontSize: 11, color, fontFamily: 'JetBrains Mono, monospace', fontWeight: 600 }}>{val.toFixed(1)}</span>
      </div>
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${val * 10}%`, background: color }} />
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: Status }) {
  const map: Record<Status, [string, string]> = {
    pending_review: ['var(--bolt-orange)', 'rgba(255,140,66,0.1)'],
    approved:       ['var(--bolt-green)',  'rgba(0,229,160,0.1)'],
    published:      ['#6BA3FF',            'rgba(107,163,255,0.1)'],
    rejected:       ['var(--bolt-red)',    'rgba(255,69,96,0.1)'],
  }
  const [color, bg] = map[status] || ['gray', 'rgba(0,0,0,0.1)']
  return (
    <span style={{ fontSize: 11, fontWeight: 600, padding: '3px 10px', borderRadius: 20, background: bg, color, border: `1px solid ${color}33` }}>
      {status.replace('_', ' ')}
    </span>
  )
}

export default function ContentManagement() {
  const [items, setItems] = useState<ContentItem[]>(DEMO_ITEMS)
  const [selected, setSelected] = useState<ContentItem | null>(null)
  const [filter, setFilter] = useState<'all' | Status>('all')

  // Load real scripts from API on mount; fall back to demo data if backend unavailable
  useEffect(() => {
    api.scripts()
      .then((data: any) => {
        if (Array.isArray(data) && data.length > 0) setItems(data)
      })
      .catch(() => {
        // Backend unavailable -- keep demo items for static preview
        fetch('/data/content.json').then(r => r.json()).then((data: any) => {
          if (Array.isArray(data) && data.length > 0) setItems(data)
        }).catch(() => {})
      })
  }, [])

  const filtered = filter === 'all' ? items : items.filter(i => i.status === filter)

  const approve = async (id: string) => {
    // Update local state immediately for instant UI feedback
    setItems(prev => prev.map(i => i.content_id === id ? { ...i, status: 'approved' } : i))
    if (selected?.content_id === id) setSelected(prev => prev ? { ...prev, status: 'approved' } : null)
    try {
      await api.approve(id)
    } catch {
      // Dashboard running statically -- show CLI instruction
      console.info(`To approve via CLI: python hitl.py approve ${id}`)
    }
  }
  const reject = async (id: string) => {
    setItems(prev => prev.map(i => i.content_id === id ? { ...i, status: 'rejected' } : i))
    if (selected?.content_id === id) setSelected(prev => prev ? { ...prev, status: 'rejected' } : null)
    try {
      await api.reject(id)
    } catch {
      console.info(`To reject via CLI: python hitl.py reject ${id}`)
    }
  }
  const publish = async (id: string) => {
    setItems(prev => prev.map(i => i.content_id === id ? { ...i, status: 'published' } : i))
    if (selected?.content_id === id) setSelected(prev => prev ? { ...prev, status: 'published' } : null)
  }

  const TABS: Array<{key: 'all'|Status; label: string}> = [
    { key: 'all', label: `All (${items.length})` },
    { key: 'pending_review', label: `Review (${items.filter(i=>i.status==='pending_review').length})` },
    { key: 'approved', label: 'Approved' },
    { key: 'published', label: 'Published' },
  ]

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 16, height: 'calc(100vh - 104px)' }}>
      {/* List */}
      <div className="bolt-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Filter tabs */}
        <div style={{ padding: '14px 14px 0', display: 'flex', gap: 4, borderBottom: '1px solid var(--bolt-border)', flexWrap: 'wrap' }}>
          {TABS.map(t => (
            <button key={t.key} onClick={() => setFilter(t.key)} style={{
              padding: '6px 12px', borderRadius: '6px 6px 0 0', fontSize: 12, fontWeight: 600,
              background: filter === t.key ? 'var(--bolt-surface-2)' : 'transparent',
              color: filter === t.key ? 'var(--bolt-yellow)' : 'var(--bolt-text-dim)',
              border: filter === t.key ? '1px solid var(--bolt-border-bright)' : '1px solid transparent',
              borderBottom: filter === t.key ? '1px solid var(--bolt-surface-2)' : 'none',
              cursor: 'pointer', fontFamily: 'Space Grotesk, sans-serif', marginBottom: filter === t.key ? -1 : 0,
            }}>
              {t.label}
            </button>
          ))}
        </div>
        {/* Items */}
        <div style={{ flex: 1, overflowY: 'auto', padding: 12 }}>
          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: '40px 20px', color: 'var(--bolt-text-muted)', fontSize: 13 }}>
              No items in this category
            </div>
          )}
          {filtered.map(item => (
            <div key={item.content_id}
              onClick={() => setSelected(item)}
              style={{
                padding: '12px', borderRadius: 8, cursor: 'pointer', marginBottom: 6,
                background: selected?.content_id === item.content_id ? 'var(--bolt-surface-2)' : 'transparent',
                border: selected?.content_id === item.content_id ? '1px solid rgba(255,255,0,0.18)' : '1px solid transparent',
                transition: 'all 0.12s',
              }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8, marginBottom: 6 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--bolt-text)', lineHeight: 1.4, flex: 1 }}>
                  {item.article.title.slice(0, 60)}{item.article.title.length > 60 ? '...' : ''}
                </div>
                <span className={`score-badge ${item.quality.overall_score >= 8.5 ? 'score-high' : 'score-mid'}`}>
                  {item.quality.overall_score.toFixed(1)}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', gap: 6 }}>
                  <span className={`tag-pill tag-${item.pillar.replace('ai_','')}`}>{item.pillar.replace('ai_','').replace('_',' ')}</span>
                  <span style={{ fontSize: 10, color: 'var(--bolt-text-muted)' }}>{item.article.source}</span>
                </div>
                <StatusBadge status={item.status} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Detail panel */}
      {selected ? (
        <div className="bolt-card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
          {/* Header */}
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--bolt-border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--bolt-text)', marginBottom: 4 }}>
                {selected.article.title.slice(0, 55)}{selected.article.title.length > 55 ? '...' : ''}
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <StatusBadge status={selected.status} />
                <span className={`tag-pill tag-${selected.pillar.replace('ai_','')}`}>{selected.pillar.replace('ai_','').replace('_',' ')}</span>
                {selected.auto_approved && <span style={{ fontSize: 10, color: 'var(--bolt-green)', fontWeight: 600 }}>AUTO-APPROVED</span>}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              {selected.status === 'pending_review' && <>
                <button className="btn-red" onClick={() => reject(selected.content_id)}>Reject</button>
                <button className="btn-green" onClick={() => approve(selected.content_id)}>Approve</button>
              </>}
              {selected.status === 'approved' && (
                <button className="btn-yellow" style={{ display:'flex', alignItems:'center', gap:6 }} onClick={() => publish(selected.content_id)}>
                  <Send size={12} /> Publish Now
                </button>
              )}
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '18px 20px', display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* HITL instruction banner for pending items */}
            {selected.status === 'pending_review' && (
              <div style={{ padding:'12px 14px', borderRadius:8, background:'rgba(255,170,0,0.08)', border:'1px solid rgba(255,170,0,0.22)', marginBottom:4 }}>
                <div style={{ fontSize:12, fontWeight:700, color:'var(--bolt-orange)', marginBottom:6 }}>⏸️ Pipeline paused — waiting for your review</div>
                <div style={{ fontSize:12, color:'var(--bolt-text-dim)', lineHeight:1.6 }}>
                  The pipeline daemon is polling every 60s for your decision. Approve to continue to video rendering, or reject to skip this script.
                </div>
                <div style={{ marginTop:8, padding:'6px 10px', background:'var(--bolt-surface-2)', borderRadius:6, fontFamily:'JetBrains Mono, monospace', fontSize:11, color:'var(--bolt-text-dim)' }}>
                  CLI: <span style={{ color:'var(--bolt-yellow)' }}>python hitl.py approve {selected.content_id}</span>
                </div>
              </div>
            )}

            {/* Script */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--bolt-text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                BOLT SCRIPT · {selected.quality.word_count} words
              </div>
              <div style={{
                background: 'var(--bolt-surface-2)', border: '1px solid var(--bolt-border-bright)',
                borderRadius: 8, padding: '14px 16px', fontSize: 14, lineHeight: 1.7, color: 'var(--bolt-text)',
              }}>
                {selected.script}
              </div>
            </div>

            {/* Quality scores */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--bolt-text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Quality Analysis
                </div>
                <span className={`score-badge ${selected.quality.overall_score >= 8.5 ? 'score-high' : 'score-mid'}`}>
                  Overall: {selected.quality.overall_score.toFixed(1)}/10
                </span>
              </div>
              <ScoreBar label="Hook Strength"  val={selected.quality.hook_strength} />
              <ScoreBar label="Simplicity"     val={selected.quality.simplicity} />
              <ScoreBar label="Bolt Voice"     val={selected.quality.bolt_voice} />
              {selected.quality.feedback && (
                <div style={{ marginTop: 8, padding: '8px 12px', borderRadius: 6, background: 'rgba(255,140,66,0.08)', border: '1px solid rgba(255,140,66,0.2)', fontSize: 12, color: 'var(--bolt-orange)' }}>
                  💡 {selected.quality.feedback}
                </div>
              )}
            </div>

            {/* Captions */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--bolt-text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                Platform Captions
              </div>
              {selected.captions.youtube?.title && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: '#FF4040', fontWeight: 600, marginBottom: 4 }}>▶ YouTube</div>
                  <div style={{ fontSize: 13, color: 'var(--bolt-text)', background: 'var(--bolt-surface-2)', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--bolt-border)' }}>
                    {selected.captions.youtube.title}
                  </div>
                </div>
              )}
              {selected.captions.tiktok?.caption && (
                <div style={{ marginBottom: 8 }}>
                  <div style={{ fontSize: 11, color: '#00F2EA', fontWeight: 600, marginBottom: 4 }}>♪ TikTok</div>
                  <div style={{ fontSize: 13, color: 'var(--bolt-text)', background: 'var(--bolt-surface-2)', padding: '8px 12px', borderRadius: 6, border: '1px solid var(--bolt-border)' }}>
                    {selected.captions.tiktok.caption}
                  </div>
                </div>
              )}
            </div>

            {/* Metadata */}
            <div style={{ fontSize: 11, color: 'var(--bolt-text-muted)', fontFamily: 'JetBrains Mono, monospace', paddingTop: 8, borderTop: '1px solid var(--bolt-border)' }}>
              ID: {selected.content_id} · Source: {selected.article.source} · Generated: {selected.generated_at.slice(0,16).replace('T',' ')} UTC
            </div>
          </div>
        </div>
      ) : (
        <div className="bolt-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
          <Zap size={32} color="rgba(255,255,0,0.2)" />
          <div style={{ fontSize: 14, color: 'var(--bolt-text-muted)' }}>Select a content item to review</div>
        </div>
      )}
    </div>
  )
}
