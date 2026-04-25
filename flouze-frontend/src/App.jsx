import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useUiStore } from './store/uiStore'
import AppShell from './components/layout/AppShell'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ExpensesPage from './pages/ExpensesPage'
import BudgetsPage from './pages/BudgetsPage'
import CategoriesPage from './pages/CategoriesPage'
import SpacesPage from './pages/SpacesPage'

function ProtectedRoute({ children }) {
  const token = useAuthStore((s) => s.accessToken)
  if (!token) return <Navigate to="/login" replace />
  return children
}

function ToastContainer() {
  const { toasts, dismissToast } = useUiStore()
  if (!toasts.length) return null
  return (
    <div className="toast-container">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`toast toast-${t.type}`}
          onClick={() => dismissToast(t.id)}
          style={{ cursor: 'pointer' }}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}

export default function App() {
  const { accessToken, fetchMe } = useAuthStore()

  // Re-hydrate user info on page load if we have a token
  useEffect(() => {
    if (accessToken) fetchMe().catch(() => {})
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="budgets" element={<BudgetsPage />} />
          <Route path="categories" element={<CategoriesPage />} />
          <Route path="spaces" element={<SpacesPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <ToastContainer />
    </>
  )
}
