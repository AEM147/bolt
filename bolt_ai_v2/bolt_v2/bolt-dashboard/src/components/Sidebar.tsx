import { Link, useLocation } from 'react-router-dom'
import { Home, FileText, BarChart3, Newspaper, Share2, DollarSign, Settings, Zap } from 'lucide-react'

const navigation = [
  { name: 'Overview',      href: '/',          icon: Home },
  { name: 'Content Queue', href: '/content',   icon: FileText },
  { name: 'Analytics',     href: '/analytics', icon: BarChart3 },
  { name: 'News Monitor',  href: '/news',      icon: Newspaper },
  { name: 'Platforms',     href: '/platforms', icon: Share2 },
  { name: 'Cost & Backups',href: '/costs',     icon: DollarSign },
  { name: 'Settings',      href: '/settings',  icon: Settings },
]

export default function Sidebar() {
  const location = useLocation()
  return (
    <div style={{ width:220,minHeight:'100vh',flexShrink:0,background:'var(--bolt-surface)',borderRight:'1px solid var(--bolt-border)',display:'flex',flexDirection:'column' }}>
      <div style={{ padding:'24px 20px 20px',borderBottom:'1px solid var(--bolt-border)' }}>
        <div style={{ display:'flex',alignItems:'center',gap:10 }}>
          <div style={{ width:34,height:34,background:'var(--bolt-yellow)',borderRadius:8,display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0 }}>
            <Zap size={18} color="#0A0A0A" fill="#0A0A0A" />
          </div>
          <div>
            <div style={{ fontSize:15,fontWeight:700,color:'var(--bolt-text)',letterSpacing:'-0.02em' }}>Bolt</div>
            <div style={{ fontSize:11,color:'var(--bolt-text-muted)',fontWeight:500 }}>AI Creator v2.1</div>
          </div>
        </div>
      </div>
      <nav style={{ flex:1,padding:'12px 10px' }}>
        {navigation.map((item) => {
          const active = location.pathname === item.href
          return (
            <Link key={item.name} to={item.href} style={{ display:'flex',alignItems:'center',gap:10,padding:'9px 12px',borderRadius:8,marginBottom:2,textDecoration:'none',fontSize:13,fontWeight:500,background:active?'var(--bolt-yellow-dim)':'transparent',color:active?'var(--bolt-yellow)':'var(--bolt-text-dim)',border:active?'1px solid rgba(255,255,0,0.18)':'1px solid transparent',transition:'all 0.15s' }}>
              <item.icon size={15} />
              {item.name}
            </Link>
          )
        })}
      </nav>
      <div style={{ padding:'14px 14px 20px',borderTop:'1px solid var(--bolt-border)' }}>
        <div style={{ display:'flex',alignItems:'center',gap:8,padding:'9px 12px',borderRadius:8,background:'rgba(0,229,160,0.06)',border:'1px solid rgba(0,229,160,0.14)' }}>
          <span className="status-dot online" />
          <span style={{ fontSize:12,color:'var(--bolt-green)',fontWeight:600 }}>Pipeline Active</span>
        </div>
        <div style={{ marginTop:8,fontSize:11,color:'var(--bolt-text-muted)',textAlign:'center',fontFamily:'JetBrains Mono,monospace' }}>
          v2.1 · All tools free
        </div>
      </div>
    </div>
  )
}
