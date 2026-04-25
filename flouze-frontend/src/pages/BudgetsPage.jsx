import Topbar from '../components/layout/Topbar'

export default function BudgetsPage() {
  return (
    <>
      <Topbar title="Budgets" />
      <div className="content">
        <div className="empty-state">
          <p>Gestion des budgets — Jalon 14</p>
        </div>
      </div>
    </>
  )
}
