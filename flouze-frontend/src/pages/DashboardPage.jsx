import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import Topbar from '../components/layout/Topbar'
import client from '../api/client'
import { useUiStore } from '../store/uiStore'

// ── helpers ──────────────────────────────────────────────────────────────────

const MONTHS_FR = ['Jan','Fév','Mar','Avr','Mai','Juin','Juil','Aoû','Sep','Oct','Nov','Déc']

function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
}

function prevMonth(m) {
  const [y, mo] = m.split('-').map(Number)
  return mo === 1
    ? `${y - 1}-12`
    : `${y}-${String(mo - 1).padStart(2, '0')}`
}

function nextMonth(m) {
  const [y, mo] = m.split('-').map(Number)
  return mo === 12
    ? `${y + 1}-01`
    : `${y}-${String(mo + 1).padStart(2, '0')}`
}

function fmtMonthLabel(m) {
  const [, mo] = m.split('-').map(Number)
  return MONTHS_FR[mo - 1]
}

function fmtMonthFull(m) {
  const [y, mo] = m.split('-').map(Number)
  return `${MONTHS_FR[mo - 1]} ${y}`
}

function fmtAmount(v, short = false) {
  const n = parseFloat(v) || 0
  if (short && n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return n.toLocaleString('fr-FR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function progressColor(spent, budget) {
  if (!budget) return 'var(--accent)'
  const pct = spent / budget
  if (pct > 1)  return 'var(--red)'
  if (pct > 0.8) return 'var(--amber)'
  return 'var(--accent)'
}

// ── sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, highlight }) {
  return (
    <div className="card" style={{ flex: 1, minWidth: 0 }}>
      <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 6 }}>{label}</p>
      <p style={{
        fontSize: 22, fontWeight: 500, letterSpacing: '-0.5px', lineHeight: 1,
        color: highlight ?? 'var(--text)',
      }}>
        {value}
      </p>
      {sub && <p style={{ fontSize: 11, color: 'var(--text3)', marginTop: 4 }}>{sub}</p>}
    </div>
  )
}

function MonthPicker({ month, onChange }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <button className="btn btn-ghost btn-icon" onClick={() => onChange(prevMonth(month))}>
        <IconChevron dir="left" />
      </button>
      <span style={{ fontSize: 13, fontWeight: 500, minWidth: 84, textAlign: 'center' }}>
        {fmtMonthFull(month)}
      </span>
      <button
        className="btn btn-ghost btn-icon"
        onClick={() => onChange(nextMonth(month))}
        disabled={month >= currentMonth()}
      >
        <IconChevron dir="right" />
      </button>
    </div>
  )
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border2)', borderRadius: 8, padding: '8px 12px', fontSize: 12 }}>
      <p style={{ color: 'var(--text2)', marginBottom: 2 }}>{label}</p>
      <p style={{ fontWeight: 600 }}>{fmtAmount(payload[0].value)} MAD</p>
    </div>
  )
}

function TrendChart({ data, activeMonth }) {
  return (
    <ResponsiveContainer width="100%" height={110}>
      <BarChart data={data} barSize={24} margin={{ top: 4, right: 0, left: -24, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11, fill: 'var(--text3)' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: 'var(--text3)' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => fmtAmount(v, true)}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: 'var(--surface2)' }} />
        <Bar dataKey="total" radius={[4, 4, 0, 0]}>
          {data.map((d) => (
            <Cell
              key={d.month}
              fill={d.month === activeMonth ? 'var(--accent)' : '#C8DFC8'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function CategoryProgress({ cat }) {
  const spent = parseFloat(cat.spent) || 0
  const budget = cat.budget ? parseFloat(cat.budget) : null
  const pct = budget ? Math.min((spent / budget) * 100, 100) : null
  const color = progressColor(spent, budget)

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 5 }}>
        <span style={{ fontSize: 13 }}>
          <span style={{ marginRight: 6 }}>{cat.emoji}</span>
          {cat.name}
        </span>
        <span style={{ fontSize: 12, color: 'var(--text2)' }}>
          {fmtAmount(cat.spent)}
          {budget ? <span style={{ color: 'var(--text3)' }}> / {fmtAmount(cat.budget)}</span> : null}
          <span style={{ color: 'var(--text3)', marginLeft: 4 }}>MAD</span>
        </span>
      </div>
      {pct !== null && (
        <div style={{ height: 6, background: 'var(--surface2)', borderRadius: 99, overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 99, transition: 'width .4s' }} />
        </div>
      )}
    </div>
  )
}

function ExpenseRow({ exp, categories }) {
  const cat = categories.find((c) => c.category_id === exp.category_id)
  return (
    <div style={rowStyle}>
      <div style={{
        ...iconStyle,
        background: cat?.bg_color ?? 'var(--surface2)',
        fontSize: 14,
      }}>
        {cat?.emoji ?? '💸'}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 13.5, fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{exp.title}</p>
        <p style={{ fontSize: 12, color: 'var(--text3)', marginTop: 1 }}>
          {exp.date} {cat ? `· ${cat.name}` : ''}
        </p>
      </div>
      <p style={{ fontSize: 14, fontWeight: 500, color: 'var(--red)', flexShrink: 0 }}>
        −{fmtAmount(exp.amount_mad)} MAD
      </p>
    </div>
  )
}

const rowStyle  = { display: 'flex', alignItems: 'center', gap: 12, padding: '11px 16px', borderBottom: '1px solid var(--border)', cursor: 'default' }
const iconStyle = { width: 34, height: 34, borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }

// ── main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [month, setMonth] = useState(currentMonth)
  const [dash, setDash] = useState(null)
  const [expenses, setExpenses] = useState([])
  const [loading, setLoading] = useState(true)
  const { toast } = useUiStore()

  useEffect(() => { load() }, [month]) // eslint-disable-line react-hooks/exhaustive-deps

  async function load() {
    setLoading(true)
    try {
      const [{ data: d }, { data: e }] = await Promise.all([
        client.get('/dashboard', { params: { month } }),
        client.get('/expenses',  { params: { month, limit: 5 } }),
      ])
      setDash(d)
      setExpenses(e)
    } catch {
      toast('Impossible de charger le tableau de bord', 'error')
    } finally {
      setLoading(false)
    }
  }

  const trendData = (dash?.monthly_trend ?? []).map((pt) => ({
    ...pt,
    total: parseFloat(pt.total) || 0,
    label: fmtMonthLabel(pt.month),
  }))

  const totalExpenses = (dash?.by_category ?? []).reduce((s, c) => s + (c.expense_count ?? 0), 0)
  const activeCategories = (dash?.by_category ?? []).filter((c) => parseFloat(c.spent) > 0)
  const restant = dash?.restant ? parseFloat(dash.restant) : null

  return (
    <>
      <Topbar
        title="Tableau de bord"
        actions={<MonthPicker month={month} onChange={setMonth} />}
      />
      <div className="content">
        {loading && !dash ? (
          <div style={{ display: 'flex', justifyContent: 'center', paddingTop: 60 }}>
            <span className="spinner" style={{ width: 28, height: 28 }} />
          </div>
        ) : (
          <>
            {/* ── Stat cards ── */}
            <div style={{ display: 'flex', gap: 14, marginBottom: 22, flexWrap: 'wrap' }}>
              <StatCard
                label="Total dépenses"
                value={`${fmtAmount(dash?.total ?? 0)} MAD`}
                sub={`${totalExpenses} transaction${totalExpenses !== 1 ? 's' : ''}`}
              />
              <StatCard
                label="Budget mensuel"
                value={dash?.budget_global ? `${fmtAmount(dash.budget_global)} MAD` : '—'}
                sub={dash?.budget_global ? 'budget configuré' : 'aucun budget'}
              />
              <StatCard
                label="Restant"
                value={restant !== null ? `${fmtAmount(restant)} MAD` : '—'}
                highlight={restant !== null ? (restant < 0 ? 'var(--red)' : 'var(--accent)') : undefined}
                sub={restant !== null ? (restant < 0 ? 'Dépassement' : 'Disponible') : ''}
              />
              <StatCard
                label="Catégories actives"
                value={activeCategories.length}
                sub={`sur ${(dash?.by_category ?? []).length} catégories`}
              />
            </div>

            {/* ── Charts row ── */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 22 }}>
              {/* Trend */}
              <div className="card">
                <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>Tendance 6 mois</p>
                <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 14 }}>
                  Évolution des dépenses
                </p>
                {trendData.length > 0
                  ? <TrendChart data={trendData} activeMonth={month} />
                  : <div className="empty-state" style={{ padding: '20px 0' }}><p>Aucune donnée</p></div>
                }
              </div>

              {/* Category budgets */}
              <div className="card">
                <p style={{ fontSize: 13, fontWeight: 500, marginBottom: 2 }}>Par catégorie</p>
                <p style={{ fontSize: 12, color: 'var(--text2)', marginBottom: 14 }}>
                  Dépenses vs budgets
                </p>
                {(dash?.by_category ?? []).filter((c) => parseFloat(c.spent) > 0 || c.budget).length === 0 ? (
                  <div className="empty-state" style={{ padding: '20px 0' }}><p>Aucune dépense ce mois</p></div>
                ) : (
                  <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                    {(dash?.by_category ?? [])
                      .filter((c) => parseFloat(c.spent) > 0 || c.budget)
                      .map((cat) => (
                        <CategoryProgress key={cat.category_id} cat={cat} />
                      ))}
                  </div>
                )}
              </div>
            </div>

            {/* ── Recent expenses ── */}
            <div>
              <div className="section-header">
                <p className="section-title">Transactions récentes</p>
              </div>
              {expenses.length === 0 ? (
                <div className="empty-state">
                  <p>Aucune dépense pour {fmtMonthFull(month)}</p>
                </div>
              ) : (
                <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', overflow: 'hidden' }}>
                  {expenses.map((exp) => (
                    <ExpenseRow key={exp.id} exp={exp} categories={dash?.by_category ?? []} />
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  )
}

function IconChevron({ dir }) {
  return (
    <svg viewBox="0 0 16 16" fill="none" width="14" height="14">
      <path
        d={dir === 'left' ? 'M10 3L5 8l5 5' : 'M6 3l5 5-5 5'}
        stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
      />
    </svg>
  )
}
