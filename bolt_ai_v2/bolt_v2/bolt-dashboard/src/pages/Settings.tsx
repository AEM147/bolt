import { useState } from 'react'
import { Save, Key, Zap, Bell, Shield } from 'lucide-react'

function Field({ label, val, onChange, type='text', mono=false }: { label:string; val:string; onChange:(v:string)=>void; type?:string; mono?:boolean }) {
  return (
    <div style={{ marginBottom:14 }}>
      <label style={{ fontSize:12, fontWeight:600, color:'var(--bolt-text-dim)', display:'block', marginBottom:6 }}>{label}</label>
      <input type={type} value={val} onChange={e => onChange(e.target.value)}
        style={{ width:'100%', padding:'9px 12px', fontSize:13, borderRadius:8,
          background:'var(--bolt-surface-2)', border:'1px solid var(--bolt-border-bright)',
          color:'var(--bolt-text)', fontFamily: mono ? 'JetBrains Mono, monospace' : 'Space Grotesk, sans-serif' }} />
    </div>
  )
}

function Toggle({ label, sub, val, onChange }: { label:string; sub:string; val:boolean; onChange:(v:boolean)=>void }) {
  return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'12px 0', borderBottom:'1px solid var(--bolt-border)' }}>
      <div>
        <div style={{ fontSize:13, fontWeight:500, color:'var(--bolt-text)' }}>{label}</div>
        <div style={{ fontSize:12, color:'var(--bolt-text-muted)' }}>{sub}</div>
      </div>
      <div onClick={() => onChange(!val)} style={{
        width:40, height:22, borderRadius:11, cursor:'pointer', position:'relative',
        background: val ? 'var(--bolt-yellow)' : 'var(--bolt-surface-3)',
        border: `1px solid ${val ? 'rgba(255,255,0,0.4)' : 'var(--bolt-border-bright)'}`,
        transition:'all 0.2s',
      }}>
        <div style={{
          position:'absolute', top:2, borderRadius:'50%', width:16, height:16,
          background: val ? '#0A0A0A' : 'var(--bolt-text-dim)',
          left: val ? 20 : 2,
          transition:'left 0.2s',
        }} />
      </div>
    </div>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title:string; children:React.ReactNode }) {
  return (
    <div className="bolt-card" style={{ padding:'18px 20px' }}>
      <div style={{ fontSize:13, fontWeight:700, color:'var(--bolt-text)', marginBottom:16, display:'flex', alignItems:'center', gap:8 }}>
        {icon} {title}
      </div>
      {children}
    </div>
  )
}

export default function Settings() {
  const [saved, setSaved] = useState(false)
  const [apiKeys, setApiKeys] = useState({ anthropic:'sk-ant-...', elevenlabs:'eleven_...', heygen:'', buffer:'' })
  const [automation, setAutomation] = useState({
    autoPublish: false, autoGenerate: true, smartSchedule: true, qualityGate: true,
    discordNotify: true, weekendPause: false,
  })
  const [threshold, setThreshold] = useState('8.5')
  const [voiceId, setVoiceId] = useState('')
  const [webhookUrl, setWebhookUrl] = useState('')

  const save = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div style={{ display:'flex', flexDirection:'column', gap:16, maxWidth:700 }}>
      <Section icon={<Key size={14} color="var(--bolt-yellow)" />} title="API Keys">
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:0 }}>
          <div style={{ paddingRight:16 }}>
            <Field label="Anthropic (Claude)" val={apiKeys.anthropic} type="password" mono onChange={v => setApiKeys(p => ({...p, anthropic:v}))} />
            <Field label="ElevenLabs Voice ID" val={voiceId} mono onChange={setVoiceId} />
            <Field label="ElevenLabs API Key"  val={apiKeys.elevenlabs} type="password" mono onChange={v => setApiKeys(p => ({...p, elevenlabs:v}))} />
          </div>
          <div style={{ paddingLeft:16, borderLeft:'1px solid var(--bolt-border)' }}>
            <Field label="HeyGen API Key"   val={apiKeys.heygen} type="password" mono onChange={v => setApiKeys(p => ({...p, heygen:v}))} />
            <Field label="Buffer Access Token" val={apiKeys.buffer} type="password" mono onChange={v => setApiKeys(p => ({...p, buffer:v}))} />
            <Field label="Discord Webhook URL" val={webhookUrl} mono onChange={setWebhookUrl} />
          </div>
        </div>
        <div style={{ padding:'8px 12px', borderRadius:6, background:'rgba(107,163,255,0.08)', border:'1px solid rgba(107,163,255,0.15)', fontSize:12, color:'#6BA3FF', marginTop:4 }}>
          ℹ️ Keys are stored in <code style={{ fontFamily:'JetBrains Mono, monospace' }}>code/config.json</code> on your server. Never commit this file to git.
        </div>
      </Section>

      <Section icon={<Zap size={14} color="var(--bolt-yellow)" />} title="Automation Controls">
        <Toggle label="Auto-generate scripts"     sub="Automatically generate scripts when news is queued" val={automation.autoGenerate} onChange={v => setAutomation(p=>({...p, autoGenerate:v}))} />
        <Toggle label="Auto-publish videos"       sub={`Auto-post when score ≥ ${threshold}/10 (currently OFF — recommended for new accounts)`} val={automation.autoPublish} onChange={v => setAutomation(p=>({...p, autoPublish:v}))} />
        <Toggle label="Smart scheduling"          sub="Post at AI-predicted optimal times for your audience" val={automation.smartSchedule} onChange={v => setAutomation(p=>({...p, smartSchedule:v}))} />
        <Toggle label="Discord notifications"     sub="Receive alerts for pipeline events and failures" val={automation.discordNotify} onChange={v => setAutomation(p=>({...p, discordNotify:v}))} />
        <Toggle label="Pause on weekends"         sub="Skip pipeline runs on Saturday and Sunday" val={automation.weekendPause} onChange={v => setAutomation(p=>({...p, weekendPause:v}))} />
        <div style={{ marginTop:16 }}>
          <Field label="Auto-publish quality threshold (0–10)" val={threshold} onChange={setThreshold} />
        </div>
      </Section>

      <Section icon={<Shield size={14} color="var(--bolt-yellow)" />} title="Character & Brand">
        <Field label="Character name" val="Bolt" onChange={() => {}} />
        <Field label="Catchphrases (comma-separated)" val="Stay curious, humans!, Let's get wired!, Bolt out!" onChange={() => {}} />
        <div style={{ marginBottom:14 }}>
          <label style={{ fontSize:12, fontWeight:600, color:'var(--bolt-text-dim)', display:'block', marginBottom:6 }}>AI Persona prompt</label>
          <textarea rows={3} defaultValue="You are BOLT — an enthusiastic AI robot news reporter with a fun, slightly robotic personality..." style={{ width:'100%', padding:'9px 12px', fontSize:13, borderRadius:8, background:'var(--bolt-surface-2)', border:'1px solid var(--bolt-border-bright)', color:'var(--bolt-text)', resize:'vertical', fontFamily:'Space Grotesk, sans-serif' }} />
        </div>
      </Section>

      <div style={{ display:'flex', justifyContent:'flex-end', gap:10 }}>
        <button className="btn-ghost">Reset to defaults</button>
        <button className="btn-yellow" onClick={save} style={{ display:'flex', alignItems:'center', gap:8 }}>
          {saved ? '✅ Saved!' : <><Save size={13} /> Save Changes</>}
        </button>
      </div>
    </div>
  )
}
