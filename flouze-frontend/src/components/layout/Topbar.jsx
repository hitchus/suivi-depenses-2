import { useEffect, useRef, useState } from 'react'
import { useNotifications } from '../../hooks/useNotifications'

// ── notification helpers ──────────────────────────────────────────────────────

function formatNotif(n) {
  const { type, payload } = n
  if (type === 'BUDGET_ALERT') {
    const spent  = parseFloat(payload.spent  ?? 0).toFixed(0)
    const budget = parseFloat(payload.budget ?? 0).toFixed(0)
    const month  = payload.month ?? ''
    return `Budget dépassé${month ? ` · ${month}` : ''} — ${spent} / ${budget} MAD`
  }
  if (type === 'MEMBER_JOINED') return 'Nouveau membre rejoint votre espace'
  if (type === 'EXPORT_READY') return 'Export prêt au téléchargement'
  return type.replace(/_/g, ' ').toLowerCase()
}

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'À l\'instant'
  if (mins < 60) return `il y a ${mins} min`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `il y a ${hrs}h`
  return `il y a ${Math.floor(hrs / 24)}j`
}

function notifIcon(type) {
  if (type === 'BUDGET_ALERT') return '⚠️'
  if (type === 'MEMBER_JOINED') return '👥'
  if (type === 'EXPORT_READY') return '📥'
  return '🔔'
}

// ── NotificationDropdown ──────────────────────────────────────────────────────

function NotificationDropdown({ notifications, unread, onMarkRead, onMarkAll }) {
  return (
    <div style={dropStyle}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderBottom: '1px solid var(--border)' }}>
        <span style={{ fontSize: 13, fontWeight: 600 }}>Notifications</span>
        {unread > 0 && (
          <button
            className="btn btn-ghost btn-sm"
            style={{ fontSize: 11, padding: '3px 8px' }}
            onClick={onMarkAll}
          >
            Tout lire
          </button>
        )}
      </div>

      {notifications.length === 0 ? (
        <div style={{ padding: '24px 16px', textAlign: 'center', color: 'var(--text3)', fontSize: 13 }}>
          Aucune notification
        </div>
      ) : (
        <div style={{ maxHeight: 320, overflowY: 'auto' }}>
          {notifications.map((n) => (
            <div
              key={n.id}
              onClick={() => !n.read_at && onMarkRead(n.id)}
              style={{
                display: 'flex', gap: 10, padding: '10px 16px',
                borderBottom: '1px solid var(--border)',
                cursor: n.read_at ? 'default' : 'pointer',
                background: n.read_at ? 'transparent' : 'var(--accent-light)',
                transition: 'background .15s',
              }}
            >
              <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>{notifIcon(n.type)}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.4 }}>
                  {formatNotif(n)}
                </p>
                <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 2 }}>
                  {timeAgo(n.created_at)}
                </p>
              </div>
              {!n.read_at && (
                <div style={{ width: 7, height: 7, borderRadius: '50%', background: 'var(--accent)', flexShrink: 0, marginTop: 5 }} />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const dropStyle = {
  position: 'absolute', top: 'calc(100% + 6px)', right: 0,
  width: 320, background: 'var(--surface)',
  border: '1px solid var(--border2)', borderRadius: 'var(--r-lg)',
  boxShadow: '0 8px 30px rgba(0,0,0,.12)', zIndex: 200,
}

// ── Topbar ────────────────────────────────────────────────────────────────────

export default function Topbar({ title, actions }) {
  const { notifications, unread, markRead, markAllRead } = useNotifications()
  const [open, setOpen] = useState(false)
  const bellRef = useRef(null)

  // Close dropdown on outside click
  useEffect(() => {
    function handler(e) {
      if (bellRef.current && !bellRef.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <header style={styles.topbar}>
      <span style={styles.title}>{title}</span>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {actions}

        {/* Notification bell */}
        <div ref={bellRef} style={{ position: 'relative' }}>
          <button
            className="btn btn-ghost btn-icon"
            onClick={() => setOpen((o) => !o)}
            title="Notifications"
            style={{ position: 'relative' }}
          >
            <IconBell />
            {unread > 0 && (
              <span style={{
                position: 'absolute', top: 3, right: 3,
                minWidth: 16, height: 16, borderRadius: 99,
                background: 'var(--red)', color: '#fff',
                fontSize: 10, fontWeight: 700, lineHeight: '16px',
                textAlign: 'center', padding: '0 3px',
              }}>
                {unread > 9 ? '9+' : unread}
              </span>
            )}
          </button>

          {open && (
            <NotificationDropdown
              notifications={notifications}
              unread={unread}
              onMarkRead={(id) => { markRead(id) }}
              onMarkAll={() => { markAllRead() }}
            />
          )}
        </div>
      </div>
    </header>
  )
}

const styles = {
  topbar: {
    height: 56, background: 'var(--surface)', borderBottom: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 24px', flexShrink: 0,
  },
  title: { fontSize: 15, fontWeight: 500 },
}

function IconBell() {
  return (
    <svg viewBox="0 0 16 16" fill="none" width="16" height="16">
      <path d="M8 2a4.5 4.5 0 0 0-4.5 4.5c0 2.5-.5 3.5-1.5 4.5h12c-1-1-1.5-2-1.5-4.5A4.5 4.5 0 0 0 8 2z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/>
      <path d="M6.5 11v.5a1.5 1.5 0 0 0 3 0V11" stroke="currentColor" strokeWidth="1.4"/>
    </svg>
  )
}
