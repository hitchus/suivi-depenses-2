import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useUiStore } from '../store/uiStore'

export default function RegisterPage() {
  const [form, setForm] = useState({ display_name: '', email: '', password: '', confirm: '' })
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const { register } = useAuthStore()
  const { toast } = useUiStore()
  const navigate = useNavigate()

  const set = (field) => (e) => setForm((f) => ({ ...f, [field]: e.target.value }))

  function validate() {
    const errs = {}
    if (!form.display_name.trim()) errs.display_name = 'Requis'
    if (!form.email.trim()) errs.email = 'Requis'
    if (form.password.length < 8) errs.password = 'Minimum 8 caractères'
    if (form.password !== form.confirm) errs.confirm = 'Les mots de passe ne correspondent pas'
    return errs
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const errs = validate()
    if (Object.keys(errs).length) { setErrors(errs); return }
    setErrors({})
    setLoading(true)
    try {
      await register(form.email, form.password, form.display_name)
      toast('Compte créé avec succès !', 'success')
      navigate('/dashboard')
    } catch (err) {
      const detail = err.response?.data?.detail
      if (typeof detail === 'string') setErrors({ _global: detail })
      else setErrors({ _global: 'Une erreur est survenue' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <div style={styles.logo}>
          <div style={styles.logoIcon}>
            <svg viewBox="0 0 16 16" fill="none" width="18" height="18">
              <path d="M3 8h10M8 3l5 5-5 5" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <span style={styles.logoText}>Flouze</span>
        </div>

        <h1 style={styles.heading}>Créer un compte</h1>
        <p style={styles.sub}>Gérez vos dépenses en toute simplicité.</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Prénom / Nom</label>
            <input className="form-input" type="text" placeholder="Jean Dupont" value={form.display_name} onChange={set('display_name')} autoFocus />
            {errors.display_name && <p className="form-error">{errors.display_name}</p>}
          </div>
          <div className="form-group">
            <label className="form-label">Adresse email</label>
            <input className="form-input" type="email" placeholder="vous@exemple.com" value={form.email} onChange={set('email')} />
            {errors.email && <p className="form-error">{errors.email}</p>}
          </div>
          <div className="form-group">
            <label className="form-label">Mot de passe</label>
            <input className="form-input" type="password" placeholder="Minimum 8 caractères" value={form.password} onChange={set('password')} />
            {errors.password && <p className="form-error">{errors.password}</p>}
          </div>
          <div className="form-group">
            <label className="form-label">Confirmer le mot de passe</label>
            <input className="form-input" type="password" placeholder="••••••••" value={form.confirm} onChange={set('confirm')} />
            {errors.confirm && <p className="form-error">{errors.confirm}</p>}
          </div>

          {errors._global && <p className="form-error" style={{ marginBottom: 12 }}>{errors._global}</p>}

          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : 'Créer mon compte'}
          </button>
        </form>

        <p style={styles.footer}>
          Déjà un compte ?{' '}
          <Link to="/login" style={styles.link}>Se connecter</Link>
        </p>
      </div>
    </div>
  )
}

const styles = {
  page: { minHeight: '100vh', background: 'var(--bg)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 },
  card: { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r-lg)', padding: '36px 32px', width: '100%', maxWidth: 400 },
  logo: { display: 'flex', alignItems: 'center', gap: 10, marginBottom: 28 },
  logoIcon: { width: 36, height: 36, background: 'var(--accent)', borderRadius: 9, display: 'flex', alignItems: 'center', justifyContent: 'center' },
  logoText: { fontFamily: 'var(--serif)', fontSize: 20, color: 'var(--text)' },
  heading: { fontSize: 20, fontWeight: 600, marginBottom: 4 },
  sub:     { fontSize: 13, color: 'var(--text2)', marginBottom: 24 },
  footer:  { marginTop: 20, fontSize: 13, color: 'var(--text2)', textAlign: 'center' },
  link:    { color: 'var(--accent)', textDecoration: 'none', fontWeight: 500 },
}
