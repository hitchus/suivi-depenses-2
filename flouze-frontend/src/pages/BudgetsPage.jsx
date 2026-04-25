import { useEffect, useState } from 'react'
import Topbar from '../components/layout/Topbar'
import client from '../api/client'
import { useUiStore } from '../store/uiStore'

// ── helpers ───────────────────────────────────────────────────────────────────

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

const MONTHS_FR = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc']
function fmtMonthFull(m) {
  const [y, mo] = m.split('-').map(Number)
  return `${MONTHS_FR[mo - 1]} ${y}`
}

function fmtAmount(v) {
  const n = parseFloat(v) || 0
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function progressColor(pct) {
  if (pct > 1)   return 'var(--red)'
  if (pct > 0.8) return 'var(--amber)'
  return 'var(--accent)'
}

// ── BudgetModal ───────────────────────────────────────────────────────────────

function BudgetModal({ month, categoryId, categoryName, current, onClose, onSaved }) {
  const [amount, setAmount] = useState(current ? String(current) : '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const { toast } = useUiStore()

  async function handleSubmit(e) {
    e.preventDefault()
    if (!amount || parseFloat(amount) <= 0) { setError('Montant requis et positif'); return }
    setError('')
    setLoading(true)
    try {
      const url = categoryId ? `/budgets/${categoryId}` : '/budgets/global'
      await client.put(url, { month, amount })
      toast('Budget enregistré', 'success')
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Erreur')
    } finally {
      setLoading(false)
    }
  }

  const title = categoryId ? `Budget — ${categoryName}` : 'Budget mensuel global'

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" style={{ maxWidth: 360 }}>
        <div className="modal-header">
          <h2 className="modal-title">{title}</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose}><IconX /></button>
        </div>
        <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 16 }}>Période : {fmtMonthFull(month)}</p>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Montant (MAD)</label>
            <input className="form-input" type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" autoFocus />
          </div>
          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}
          <div className="modal-footer">
            <button type="button" className="btn" onClick={onClose}>Annuler</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" style={{ width: 14, height: 14 }} /> : 'Enregistrer'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── CategoryBudgetCard ────────────────────────────────────────────────────────

function CategoryBudgetCard({ cat, onEdit }) {
  const spent  = parseFloat(cat.spent)  || 0
  const budget = cat.budget ? parseFloat(cat.budget) : null
  const pct    = budget ? spent / budget : null
  const color  = pct !== null ? progressColor(pct) : 'var(--text3)'
  const pctDisplay = pct !== null ? Math.round(pct * 100) : null

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 20 }}>{cat.emoji}</span>
          <div>
            <p style={{ fontSize: 13.5, fontWeight: 500 }}>{cat.name}</p>
            <p style={{ fontSize: 11, color: 'var(--text3)' }}>
              {cat.expense_count ?? 0} transaction{cat.expense_count !== 1 ? 's' : ''}
            </p>
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onEdit}>
          {budget ? 'Modifier' : 'Définir'}
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <span style={{ fontSize: 18, fontWeight: 500, color }}>
          {fmtAmount(cat.spent)} MAD
        </span>
        <span style={{ fontSize: 12, color: 'var(--text2)' }}>
          {budget ? `/ ${fmtAmount(cat.budget)} MAD` : 'Pas de budget'}
        </span>
      </div>

      {pct !== null && (
        <>
          <div style={{ height: 6, background: 'var(--surface2)', borderRadius: 99, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${Math.min(pct * 100, 100)}%`, background: color, borderRadius: 99, transition: 'width .4s' }} />
          </div>
          <p style={{ fontSize: 11, color }}>
            {pct > 1
              ? `Dépassement de ${fmtAmount(spent - budget)} MAD`
              : `${pctDisplay}% utilisé — ${fmtAmount(budget - spent)} MAD restant`}
          </p>
        </>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function BudgetsPage() {
  const [month, setMonth] = useState(currentMonth)
  const [dash, setDash]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [modal, setModal] = useState(null) // { categoryId?, categoryName?, current? }
  const { toast } = useUiStore()

  useEffect(() => { load() }, [month]) // eslint-disable-line react-hooks/exhaustive-deps

  async function load() {
    setLoading(true)
    try {
      const { data } = await client.get('/dashboard', { params: { month } })
      setDash(data)
    } catch {
      toast('Erreur de chargement', 'error')
    } finally {
      setLoading(false)
    }
  }

  function afterSave() {
    setModal(null)
    load()
  }

  const global    = dash?.budget_global ? parseFloat(dash.budget_global) : null
  const total     = parseFloat(dash?.total ?? 0)
  const restant   = global !== null ? global - total : null
  const globalPct = global ? total / global : null

  return (
    <>
      <Topbar
        title="Budgets"
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <input
              type="month" value={month}
              onChange={(e) => setMonth(e.target.value)}
              className="form-input" style={{ width: 'auto' }}
            />
            <button className="btn btn-primary" onClick={() => setModal({ categoryId: null, categoryName: null, current: global })}>
              <IconEdit /> Budget global
            </button>
          </div>
        }
      />

      <div className="content">
        {loading && !dash ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : (
          <>
            {/* ── Global budget card ── */}
            <div className="card" style={{ marginBottom: 22, display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 24, flexWrap: 'wrap' }}>
              <div>
                <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 4 }}>Budget mensuel global — {fmtMonthFull(month)}</p>
                <p style={{ fontSize: 26, fontWeight: 500, letterSpacing: '-0.5px' }}>
                  {global ? `${fmtAmount(global)} MAD` : 'Non défini'}
                </p>
              </div>
              <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                <div>
                  <p style={{ fontSize: 11, color: 'var(--text3)' }}>Dépensé</p>
                  <p style={{ fontSize: 16, fontWeight: 500 }}>{fmtAmount(total)} MAD</p>
                </div>
                {restant !== null && (
                  <div>
                    <p style={{ fontSize: 11, color: 'var(--text3)' }}>Restant</p>
                    <p style={{ fontSize: 16, fontWeight: 500, color: restant < 0 ? 'var(--red)' : 'var(--accent)' }}>
                      {fmtAmount(restant)} MAD
                    </p>
                  </div>
                )}
              </div>
              {globalPct !== null && (
                <div style={{ width: '100%' }}>
                  <div style={{ height: 8, background: 'var(--surface2)', borderRadius: 99, overflow: 'hidden' }}>
                    <div style={{
                      height: '100%', borderRadius: 99, transition: 'width .4s',
                      width: `${Math.min(globalPct * 100, 100)}%`,
                      background: progressColor(globalPct),
                    }} />
                  </div>
                  <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>
                    {Math.round(globalPct * 100)}% du budget mensuel utilisé
                  </p>
                </div>
              )}
            </div>

            {/* ── Per-category grid ── */}
            <div className="section-header">
              <p className="section-title">Par catégorie</p>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 14 }}>
              {(dash?.by_category ?? []).map((cat) => (
                <CategoryBudgetCard
                  key={cat.category_id}
                  cat={cat}
                  onEdit={() => setModal({ categoryId: cat.category_id, categoryName: cat.name, current: cat.budget ? parseFloat(cat.budget) : null })}
                />
              ))}
            </div>
          </>
        )}
      </div>

      {modal !== undefined && modal !== null && (
        <BudgetModal
          month={month}
          categoryId={modal.categoryId}
          categoryName={modal.categoryName}
          current={modal.current}
          onClose={() => setModal(null)}
          onSaved={afterSave}
        />
      )}
    </>
  )
}

function IconEdit() { return <svg viewBox="0 0 16 16" fill="none" width="13" height="13"><path d="M11 2l3 3-8 8H3v-3l8-8z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round"/></svg> }
function IconX()    { return <svg viewBox="0 0 16 16" fill="none" width="14" height="14"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg> }
