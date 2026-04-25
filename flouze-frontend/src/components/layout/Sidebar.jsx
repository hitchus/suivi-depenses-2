import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useUiStore } from '../../store/uiStore'

const NAV = [
  {
    label: 'Principal',
    items: [
      { to: '/dashboard', label: 'Tableau de bord', icon: IconDashboard },
      { to: '/expenses',  label: 'Dépenses',        icon: IconExpenses },
    ],
  },
  {
    label: 'Finances',
    items: [
      { to: '/budgets',    label: 'Budgets',    icon: IconBudgets },
      { to: '/categories', label: 'Catégories', icon: IconCategories },
    ],
  },
  {
    label: 'Collaboration',
    items: [
      { to: '/spaces', label: 'Espaces', icon: IconSpaces },
    ],
  },
]

export default function Sidebar() {
  const user = useAuthStore((s) => s.user)
  const { logout } = useAuthStore()
  const { toast } = useUiStore()
  const navigate = useNavigate()

  const initials = user?.display_name
    ? user.display_name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
    : '?'

  async function handleLogout() {
    await logout()
    toast('Déconnexion réussie', 'success')
    navigate('/login')
  }

  return (
    <aside style={styles.sidebar}>
      <div style={styles.logo}>
        <div style={styles.logoMark}>
          <div style={styles.logoIcon}>
            <svg viewBox="0 0 16 16" fill="none" width="16" height="16">
              <path d="M3 8h10M8 3l5 5-5 5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={styles.logoText}>Flouze</span>
        </div>
      </div>

      <nav style={styles.nav}>
        {NAV.map((section) => (
          <div key={section.label}>
            <p style={styles.sectionLabel}>{section.label}</p>
            {section.items.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                style={({ isActive }) => ({
                  ...styles.navItem,
                  ...(isActive ? styles.navItemActive : {}),
                })}
              >
                <Icon />
                {label}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div style={styles.footer}>
        <div style={styles.userRow} onClick={handleLogout} title="Se déconnecter">
          <div style={styles.avatar}>{initials}</div>
          <div>
            <div style={styles.userName}>{user?.display_name ?? '—'}</div>
            <div style={styles.userSub}>Se déconnecter</div>
          </div>
        </div>
      </div>
    </aside>
  )
}

const styles = {
  sidebar: { width: 220, flexShrink: 0, background: 'var(--surface)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' },
  logo: { padding: '20px 20px 16px', borderBottom: '1px solid var(--border)' },
  logoMark: { display: 'flex', alignItems: 'center', gap: 10 },
  logoIcon: { width: 32, height: 32, background: 'var(--accent)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  logoText: { fontFamily: 'var(--serif)', fontSize: 17, color: 'var(--text)', letterSpacing: '-0.3px' },
  nav: { padding: '12px 10px', flex: 1, overflowY: 'auto' },
  sectionLabel: { fontSize: 10, fontWeight: 500, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: 1, padding: '8px 10px 4px' },
  navItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '9px 10px', borderRadius: 8, cursor: 'pointer', color: 'var(--text2)', fontSize: 13.5, textDecoration: 'none', marginBottom: 1, transition: 'background .15s, color .15s' },
  navItemActive: { background: 'var(--accent-light)', color: 'var(--accent)', fontWeight: 500 },
  footer: { padding: '12px 10px', borderTop: '1px solid var(--border)' },
  userRow: { display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', borderRadius: 8, cursor: 'pointer' },
  avatar: { width: 30, height: 30, borderRadius: '50%', background: 'var(--purple-light)', color: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600, flexShrink: 0 },
  userName: { fontSize: 13, fontWeight: 500, color: 'var(--text)' },
  userSub: { fontSize: 11, color: 'var(--text3)' },
}

function IconDashboard() {
  return <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><rect x="1" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><rect x="9" y="1" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><rect x="1" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/><rect x="9" y="9" width="6" height="6" rx="1.5" stroke="currentColor" strokeWidth="1.4"/></svg>
}
function IconExpenses() {
  return <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><path d="M2 4h12M2 8h8M2 12h6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/></svg>
}
function IconBudgets() {
  return <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4"/><path d="M8 5v3l2 2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
}
function IconCategories() {
  return <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><path d="M2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/></svg>
}
function IconSpaces() {
  return <svg viewBox="0 0 16 16" fill="none" width="16" height="16"><circle cx="5" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.4"/><circle cx="11" cy="6" r="2.5" stroke="currentColor" strokeWidth="1.4"/><path d="M1 13c0-2 1.8-3.5 4-3.5M15 13c0-2-1.8-3.5-4-3.5M8 13c0-2-1.8-3.5-4-3.5M8 13c0-2 1.8-3.5 4-3.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg>
}
