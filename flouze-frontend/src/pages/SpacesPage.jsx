import { useEffect, useState } from 'react'
import Topbar from '../components/layout/Topbar'
import client from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useUiStore } from '../store/uiStore'

// ── CreateSpaceModal ──────────────────────────────────────────────────────────

function CreateSpaceModal({ onClose, onSaved }) {
  const [name, setName]   = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { toast } = useUiStore()

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) { setError('Le nom est requis'); return }
    setLoading(true)
    try {
      await client.post('/spaces', { name: name.trim() })
      toast('Espace créé', 'success')
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 360 }}>
        <div className="modal-header">
          <h2 className="modal-title">Nouvel espace</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Nom de l'espace</label>
            <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ex: Couple, Famille, Coloc…" autoFocus />
          </div>
          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Créer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── InviteModal ───────────────────────────────────────────────────────────────

function InviteModal({ space, onClose, onSaved }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const { toast } = useUiStore()

  async function handleSubmit(e) {
    e.preventDefault()
    if (!email.trim()) { setError('Email requis'); return }
    setLoading(true)
    try {
      await client.post(`/spaces/${space.id}/invite`, { email: email.trim() })
      toast('Invitation envoyée', 'success')
      onSaved()
    } catch (err) {
      const detail = err.response?.data?.detail
      if (err.response?.status === 404) setError('Aucun compte avec cet email')
      else if (err.response?.status === 409) setError('Déjà membre de cet espace')
      else setError(typeof detail === 'string' ? detail : 'Erreur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 360 }}>
        <div className="modal-header">
          <h2 className="modal-title">Inviter dans «{space.name}»</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Adresse email</label>
            <input className="form-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="ami@exemple.com" autoFocus />
          </div>
          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Inviter'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── SpaceCard ─────────────────────────────────────────────────────────────────

function SpaceCard({ space, currentUserId, onInvite }) {
  const isOwner = space.owner_id === currentUserId
  const memberCount = space.member_count ?? '—'

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--purple-light)', color: 'var(--purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
            🏠
          </div>
          <div>
            <p style={{ fontSize: 14, fontWeight: 600 }}>{space.name}</p>
            <p style={{ fontSize: 11, color: 'var(--text3)' }}>
              {isOwner ? 'Administrateur' : 'Membre'}
            </p>
          </div>
        </div>
        {isOwner && (
          <button className="btn btn-sm" onClick={() => onInvite(space)}>
            <IconUserPlus /> Inviter
          </button>
        )}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        <div>
          <p style={{ fontSize: 11, color: 'var(--text3)' }}>Membres</p>
          <p style={{ fontSize: 15, fontWeight: 500 }}>{memberCount}</p>
        </div>
        <div>
          <p style={{ fontSize: 11, color: 'var(--text3)' }}>Rôle</p>
          <span style={{
            fontSize: 11, padding: '2px 8px', borderRadius: 99,
            background: isOwner ? 'var(--accent-light)' : 'var(--surface2)',
            color: isOwner ? 'var(--accent)' : 'var(--text2)',
            fontWeight: 500,
          }}>
            {isOwner ? 'Admin' : 'Membre'}
          </span>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SpacesPage() {
  const [spaces, setSpaces]   = useState([])
  const [loading, setLoading] = useState(true)
  const [modal, setModal]     = useState(null) // 'create' | { type: 'invite', space }
  const user = useAuthStore((s) => s.user)
  const { toast } = useUiStore()

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/spaces')
      setSpaces(data)
    } catch {
      toast('Erreur de chargement', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <Topbar
        title="Espaces partagés"
        actions={
          <button className="btn btn-primary" onClick={() => setModal('create')}>
            <IconPlus /> Nouvel espace
          </button>
        }
      />
      <div className="content">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : spaces.length === 0 ? (
          <div className="empty-state">
            <p style={{ fontSize: 24, marginBottom: 8 }}>🏠</p>
            <p>Aucun espace partagé</p>
            <p style={{ marginTop: 4 }}>Créez un espace pour partager vos dépenses avec d'autres personnes.</p>
            <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setModal('create')}>
              <IconPlus /> Créer un espace
            </button>
          </div>
        ) : (
          <>
            <p style={{ fontSize: 13, color: 'var(--text2)', marginBottom: 16 }}>
              {spaces.length} espace{spaces.length > 1 ? 's' : ''} partagé{spaces.length > 1 ? 's' : ''}
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 14 }}>
              {spaces.map((s) => (
                <SpaceCard
                  key={s.id}
                  space={s}
                  currentUserId={user?.id}
                  onInvite={(sp) => setModal({ type: 'invite', space: sp })}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {modal === 'create' && (
        <CreateSpaceModal onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
      {modal?.type === 'invite' && (
        <InviteModal space={modal.space} onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
    </>
  )
}

function IconPlus()     { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg> }
function IconUserPlus() { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><circle cx="6" cy="5" r="3" stroke="currentColor" strokeWidth="1.4"/><path d="M1 14c0-3 2-5 5-5M11 9v6M14 12H8" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg> }
function IconX()        { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg> }
