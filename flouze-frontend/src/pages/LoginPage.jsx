import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useUiStore } from '../store/uiStore'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuthStore()
  const { toast } = useUiStore()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      toast('Bienvenue !', 'success')
      navigate('/dashboard')
    } catch (err) {
      const msg = err.response?.data?.detail ?? 'Identifiants invalides'
      setError(typeof msg === 'string' ? msg : 'Identifiants invalides')
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

        <h1 style={styles.heading}>Connexion</h1>
        <p style={styles.sub}>Bienvenue, connectez-vous pour continuer.</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Adresse email</label>
            <input
              className="form-input"
              type="email"
              placeholder="vous@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoFocus
            />
          </div>
          <div className="form-group">
            <label className="form-label">Mot de passe</label>
            <input
              className="form-input"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && <p className="form-error" style={{ marginBottom: 12 }}>{error}</p>}

          <button className="btn btn-primary" style={{ width: '100%', justifyContent: 'center' }} disabled={loading}>
            {loading ? <span className="spinner" style={{ width: 16, height: 16 }} /> : 'Se connecter'}
          </button>
        </form>

        <p style={styles.footer}>
          Pas encore de compte ?{' '}
          <Link to="/register" style={styles.link}>Créer un compte</Link>
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
