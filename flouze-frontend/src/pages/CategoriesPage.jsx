import { useEffect, useState } from 'react'
import Topbar from '../components/layout/Topbar'
import client from '../api/client'
import { useUiStore } from '../store/uiStore'

// ── CategoryModal ─────────────────────────────────────────────────────────────

const PRESET_COLORS = [
  { color: '#2D5F3F', bg: '#EAF3DE' },
  { color: '#D85A30', bg: '#FAECE7' },
  { color: '#BA7517', bg: '#FAEEDA' },
  { color: '#534AB7', bg: '#EEEDFE' },
  { color: '#1A73A8', bg: '#E3F0FB' },
  { color: '#8B2FC9', bg: '#F5EBFD' },
  { color: '#C0392B', bg: '#FDEBEA' },
  { color: '#16A085', bg: '#E0F7F2' },
]

const EMPTY = { name: '', emoji: '💰', color: '#2D5F3F', bg_color: '#EAF3DE' }

function CategoryModal({ category, onClose, onSaved }) {
  const isEdit = !!category
  const [form, setForm] = useState(
    isEdit
      ? { name: category.name, emoji: category.emoji, color: category.color, bg_color: category.bg_color }
      : { ...EMPTY }
  )
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const { toast } = useUiStore()

  const set = (f) => (e) => setForm((p) => ({ ...p, [f]: e.target.value }))

  function pickPreset(p) {
    setForm((prev) => ({ ...prev, color: p.color, bg_color: p.bg }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setError('Le nom est requis'); return }
    setError('')
    setLoading(true)
    try {
      if (isEdit) {
        await client.patch(`/categories/${category.id}`, form)
        toast('Catégorie mise à jour', 'success')
      } else {
        await client.post('/categories', form)
        toast('Catégorie créée', 'success')
      }
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 400 }}>
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Modifier la catégorie' : 'Nouvelle catégorie'}</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Nom</label>
              <input className="form-input" value={form.name} onChange={set('name')} placeholder="Ex: Alimentation" autoFocus />
            </div>
            <div className="form-group">
              <label className="form-label">Emoji</label>
              <input className="form-input" value={form.emoji} onChange={set('emoji')} maxLength={2} style={{ textAlign: 'center', fontSize: 18 }} />
            </div>
          </div>

          {/* Color preset picker */}
          <div className="form-group">
            <label className="form-label">Couleur</label>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {PRESET_COLORS.map((p) => (
                <button
                  key={p.color}
                  type="button"
                  onClick={() => pickPreset(p)}
                  style={{
                    width: 28, height: 28, borderRadius: 8,
                    background: p.bg, border: `2px solid ${form.color === p.color ? p.color : 'transparent'}`,
                    cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  }}
                >
                  <div style={{ width: 10, height: 10, borderRadius: '50%', background: p.color }} />
                </button>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div style={{ marginBottom: 16 }}>
            <label className="form-label">Aperçu</label>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 12px', borderRadius: 99, background: form.bg_color, color: form.color, fontSize: 13, fontWeight: 500 }}>
              {form.emoji} {form.name || 'Catégorie'}
            </span>
          </div>

          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : (isEdit ? 'Enregistrer' : 'Créer')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function CategoriesPage() {
  const [categories, setCategories] = useState([])
  const [loading, setLoading]       = useState(true)
  const [modal, setModal]           = useState(null)
  const { toast } = useUiStore()

  useEffect(() => { load() }, [])

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/categories')
      setCategories(data)
    } catch {
      toast('Erreur de chargement', 'error')
    } finally {
      setLoading(false)
    }
  }

  async function archive(cat) {
    try {
      await client.delete(`/categories/${cat.id}`)
      toast('Catégorie archivée', 'success')
      load()
    } catch {
      toast('Erreur lors de l\'archivage', 'error')
    }
  }

  return (
    <>
      <Topbar
        title="Catégories"
        actions={
          <button className="btn btn-primary" onClick={() => setModal({ type: 'add' })}>
            <IconPlus /> Nouvelle catégorie
          </button>
        }
      />
      <div className="content">
        {loading ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : categories.length === 0 ? (
          <div className="empty-state"><p>Aucune catégorie</p></div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 14 }}>
            {categories.map((cat) => (
              <div key={cat.id} className="card" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: cat.bg_color, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18, flexShrink: 0 }}>
                  {cat.emoji}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13.5, fontWeight: 500 }}>{cat.name}</p>
                  <span style={{ fontSize: 11, color: cat.color }}>●</span>
                  <span style={{ fontSize: 11, color: 'var(--text3)', marginLeft: 4 }}>
                    {cat.owner_id ? 'Personnelle' : 'Partagée'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 2, flexShrink: 0 }}>
                  <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal({ type: 'edit', category: cat })} title="Modifier">
                    <IconEdit />
                  </button>
                  <button className="btn btn-ghost btn-icon btn-sm" style={{ color: 'var(--text3)' }} onClick={() => archive(cat)} title="Archiver">
                    <IconArchive />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {modal?.type === 'add' && (
        <CategoryModal onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
      {modal?.type === 'edit' && (
        <CategoryModal category={modal.category} onClose={() => setModal(null)} onSaved={() => { setModal(null); load() }} />
      )}
    </>
  )
}

function IconPlus()    { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg> }
function IconEdit()    { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg> }
function IconArchive() { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M2 4h12v2H2zM3 6v7h10V6" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/><path d="M6 9h4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg> }
function IconX()       { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg> }
