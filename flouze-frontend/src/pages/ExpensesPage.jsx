import { useCallback, useEffect, useRef, useState } from 'react'
import Topbar from '../components/layout/Topbar'
import client from '../api/client'
import { useUiStore } from '../store/uiStore'

async function downloadExport(month, format = 'xlsx') {
  const { data } = await client.get('/expenses/export', {
    params: { format, month },
    responseType: 'blob',
  })
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = `flouze_${month}.${format}`
  a.click()
  URL.revokeObjectURL(url)
}

// ── helpers ───────────────────────────────────────────────────────────────────

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function fmtAmount(v) {
  const n = parseFloat(v) || 0
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ── ExpenseModal ──────────────────────────────────────────────────────────────

const EMPTY_FORM = { title: '', amount: '', currency: 'MAD', date: '', category_id: '', note: '' }

function ExpenseModal({ expense, categories, onClose, onSaved }) {
  const isEdit = !!expense
  const [form, setForm] = useState(
    isEdit
      ? { title: expense.title, amount: String(expense.amount), currency: expense.currency, date: expense.date, category_id: expense.category_id ?? '', note: expense.note ?? '' }
      : { ...EMPTY_FORM, date: new Date().toISOString().slice(0, 10) }
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { toast } = useUiStore()

  const set = (f) => (e) => setForm((prev) => ({ ...prev, [f]: e.target.value }))

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.title.trim() || !form.amount || !form.date) {
      setError('Titre, montant et date sont requis.')
      return
    }
    setError('')
    setLoading(true)
    try {
      const payload = {
        title: form.title.trim(),
        amount: form.amount,
        currency: form.currency,
        date: form.date,
        category_id: form.category_id || null,
        note: form.note || null,
      }
      if (isEdit) {
        await client.patch(`/expenses/${expense.id}`, payload)
        toast('Dépense mise à jour', 'success')
      } else {
        await client.post('/expenses', payload)
        toast('Dépense ajoutée', 'success')
      }
      onSaved()
    } catch (err) {
      const detail = err.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Une erreur est survenue')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Modifier la dépense' : 'Nouvelle dépense'}</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Titre</label>
            <input className="form-input" value={form.title} onChange={set('title')} placeholder="Ex: Courses Carrefour" autoFocus />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div className="form-group">
              <label className="form-label">Montant</label>
              <input className="form-input" type="number" step="0.01" min="0.01" value={form.amount} onChange={set('amount')} placeholder="0.00" />
            </div>
            <div className="form-group">
              <label className="form-label">Devise</label>
              <select className="form-input" value={form.currency} onChange={set('currency')}>
                {['MAD','EUR','USD','GBP','CHF','CAD'].map((c) => <option key={c}>{c}</option>)}
              </select>
            </div>
          </div>
          <div className="form-group">
            <label className="form-label">Date</label>
            <input className="form-input" type="date" value={form.date} onChange={set('date')} />
          </div>
          <div className="form-group">
            <label className="form-label">Catégorie</label>
            <select className="form-input" value={form.category_id} onChange={set('category_id')}>
              <option value="">Sans catégorie</option>
              {categories.map((c) => <option key={c.id} value={c.id}>{c.emoji} {c.name}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Note <span style={{ color: 'var(--text3)' }}>(optionnel)</span></label>
            <input className="form-input" value={form.note} onChange={set('note')} placeholder="Remarque…" />
          </div>

          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}

          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : (isEdit ? 'Enregistrer' : 'Ajouter')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── DeleteConfirm ─────────────────────────────────────────────────────────────

function DeleteConfirm({ expense, onClose, onDeleted }) {
  const [loading, setLoading] = useState(false)
  const { toast } = useUiStore()

  async function confirm() {
    setLoading(true)
    try {
      await client.delete(`/expenses/${expense.id}`)
      toast('Dépense supprimée', 'success')
      onDeleted()
    } catch {
      toast('Erreur lors de la suppression', 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 360 }}>
        <div className="modal-header">
          <h2 className="modal-title">Supprimer la dépense</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text2)' }}>
          Voulez-vous vraiment supprimer <strong>«{expense.title}»</strong> ? Cette action est irréversible.
        </p>
        <div className="modal-footer">
          <button className="btn" onClick={onClose}>Annuler</button>
          <button className="btn btn-danger" onClick={confirm} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Supprimer'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

const PAGE = 20

export default function ExpensesPage() {
  const [expenses, setExpenses] = useState([])
  const [categories, setCategories] = useState([])
  const [month, setMonth]   = useState(currentMonth)
  const [catFilter, setCat] = useState('')
  const [q, setQ]           = useState('')
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(false)
  const [modal, setModal]   = useState(null) // null | { type: 'add'|'edit'|'delete', expense? }
  const [exporting, setExporting] = useState(false)
  const { toast } = useUiStore()

  async function handleExport() {
    setExporting(true)
    try {
      await downloadExport(month)
    } catch {
      toast('Erreur lors de l\'export', 'error')
    } finally {
      setExporting(false)
    }
  }
  const searchTimer = useRef(null)

  // Load categories once
  useEffect(() => {
    client.get('/categories').then(({ data }) => setCategories(data)).catch(() => {})
  }, [])

  // Reload when filters change
  useEffect(() => {
    setExpenses([])
    setOffset(0)
    setHasMore(true)
    load(0, true)
  }, [month, catFilter, q]) // eslint-disable-line react-hooks/exhaustive-deps

  const load = useCallback(async (off = 0, reset = false) => {
    setLoading(true)
    try {
      const params = { month, limit: PAGE, offset: off }
      if (catFilter) params.category_id = catFilter
      if (q)         params.q = q
      const { data } = await client.get('/expenses', { params })
      setExpenses((prev) => reset ? data : [...prev, ...data])
      setHasMore(data.length === PAGE)
    } catch {
      toast('Erreur de chargement', 'error')
    } finally {
      setLoading(false)
    }
  }, [month, catFilter, q]) // eslint-disable-line react-hooks/exhaustive-deps

  function handleSearchChange(e) {
    const val = e.target.value
    clearTimeout(searchTimer.current)
    searchTimer.current = setTimeout(() => setQ(val), 350)
  }

  function loadMore() {
    const next = offset + PAGE
    setOffset(next)
    load(next)
  }

  function afterSave() {
    setModal(null)
    setExpenses([])
    setOffset(0)
    setHasMore(true)
    load(0, true)
  }

  const catMap = Object.fromEntries(categories.map((c) => [c.id, c]))

  return (
    <>
      <Topbar
        title="Dépenses"
        actions={
          <>
            <button className="btn" onClick={handleExport} disabled={exporting} title="Télécharger XLSX">
              {exporting ? <span className="spinner" style={{ width: 13, height: 13 }} /> : <IconDownload />}
              Export
            </button>
            <button className="btn btn-primary" onClick={() => setModal({ type: 'add' })}>
              <IconPlus /> Nouvelle dépense
            </button>
          </>
        }
      />

      <div className="content">
        {/* ── Filters ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 18, flexWrap: 'wrap' }}>
          <input
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
            className="form-input"
            style={{ width: 'auto' }}
          />
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', flex: 1 }}>
            <button
              className={`btn btn-sm${catFilter === '' ? ' btn-primary' : ''}`}
              onClick={() => setCat('')}
            >
              Toutes
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                className={`btn btn-sm${catFilter === c.id ? ' btn-primary' : ''}`}
                onClick={() => setCat(catFilter === c.id ? '' : c.id)}
                style={catFilter === c.id ? {} : { background: c.bg_color, color: c.color, borderColor: 'transparent' }}
              >
                {c.emoji} {c.name}
              </button>
            ))}
          </div>
          <div style={searchBoxStyle}>
            <IconSearch />
            <input
              style={{ border: 'none', outline: 'none', background: 'transparent', fontFamily: 'var(--font)', fontSize: 13, color: 'var(--text)', width: 160 }}
              placeholder="Rechercher…"
              onChange={handleSearchChange}
            />
          </div>
        </div>

        {/* ── Table ── */}
        <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
          {/* Header */}
          <div style={theadStyle}>
            <span></span>
            <span style={thStyle}>Titre</span>
            <span style={{ ...thStyle, textAlign: 'center' }}>Catégorie</span>
            <span style={thStyle}>Date</span>
            <span style={{ ...thStyle, textAlign: 'right' }}>Montant</span>
            <span style={{ ...thStyle, textAlign: 'right' }}>MAD</span>
            <span></span>
          </div>

          {expenses.length === 0 && !loading && (
            <div className="empty-state">
              <p>Aucune dépense pour cette période</p>
            </div>
          )}

          {expenses.map((exp) => {
            const cat = catMap[exp.category_id]
            return (
              <div key={exp.id} style={trowStyle}>
                <div style={{ width: 34, height: 34, borderRadius: 9, background: cat?.bg_color ?? 'var(--surface2)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0 }}>
                  {cat?.emoji ?? '💸'}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <p style={{ fontSize: 13.5, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{exp.title}</p>
                  {exp.note && <p style={{ fontSize: 11, color: 'var(--text3)' }}>{exp.note}</p>}
                </div>
                <div style={{ width: 120 }}>
                  {cat
                    ? <span style={{ fontSize: 11, padding: '2px 8px', borderRadius: 99, background: cat.bg_color, color: cat.color }}>{cat.name}</span>
                    : <span style={{ fontSize: 11, color: 'var(--text3)' }}>—</span>}
                </div>
                <span style={{ fontSize: 12.5, color: 'var(--text2)', width: 90 }}>{exp.date}</span>
                <span style={{ fontSize: 13.5, fontWeight: 500, textAlign: 'right', width: 110 }}>
                  {fmtAmount(exp.amount)} {exp.currency !== 'MAD' && <span style={{ fontSize: 11, color: 'var(--text3)' }}>{exp.currency}</span>}
                </span>
                <span style={{ fontSize: 13, color: 'var(--text2)', textAlign: 'right', width: 100 }}>
                  {fmtAmount(exp.amount_mad)} MAD
                </span>
                <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                  <button className="btn btn-ghost btn-icon btn-sm" onClick={() => setModal({ type: 'edit', expense: exp })} title="Modifier">
                    <IconEdit />
                  </button>
                  <button className="btn btn-ghost btn-icon btn-sm" style={{ color: 'var(--red)' }} onClick={() => setModal({ type: 'delete', expense: exp })} title="Supprimer">
                    <IconTrash />
                  </button>
                </div>
              </div>
            )
          })}

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 16 }}>
              <span className="spinner" />
            </div>
          )}
        </div>

        {hasMore && !loading && expenses.length > 0 && (
          <div style={{ textAlign: 'center', marginTop: 16 }}>
            <button className="btn" onClick={loadMore}>Charger plus</button>
          </div>
        )}
      </div>

      {modal?.type === 'add' && (
        <ExpenseModal categories={categories} onClose={() => setModal(null)} onSaved={afterSave} />
      )}
      {modal?.type === 'edit' && (
        <ExpenseModal expense={modal.expense} categories={categories} onClose={() => setModal(null)} onSaved={afterSave} />
      )}
      {modal?.type === 'delete' && (
        <DeleteConfirm expense={modal.expense} onClose={() => setModal(null)} onDeleted={afterSave} />
      )}
    </>
  )
}

const theadStyle = { display: 'grid', gridTemplateColumns: '34px 1fr 120px 90px 110px 100px 68px', alignItems: 'center', gap: 14, padding: '10px 16px', borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }
const thStyle    = { fontSize: 11, fontWeight: 500, color: 'var(--text3)', textTransform: 'uppercase', letterSpacing: '.5px' }
const trowStyle  = { display: 'grid', gridTemplateColumns: '34px 1fr 120px 90px 110px 100px 68px', alignItems: 'center', gap: 14, padding: '11px 16px', borderBottom: '1px solid var(--border)' }
const searchBoxStyle = { display: 'flex', alignItems: 'center', gap: 8, padding: '7px 12px', borderRadius: 8, border: '1px solid var(--border2)', background: 'var(--surface)', color: 'var(--text2)' }

function IconPlus()     { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/></svg> }
function IconEdit()     { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg> }
function IconTrash()    { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M3 5h10M6 5V3h4v2M6 8v4M10 8v4M4 5l1 9h6l1-9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/></svg> }
function IconSearch()   { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><circle cx="7" cy="7" r="4.5" stroke="currentColor" strokeWidth="1.4"/><path d="M10.5 10.5L14 14" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg> }
function IconX()        { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg> }
function IconDownload() { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M8 3v7M5 7l3 3 3-3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/><path d="M3 12h10" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/></svg> }
