import Topbar from '../components/layout/Topbar'

export default function ExpensesPage() {
  return (
    <>
      <Topbar title="Dépenses" />
      <div className="content">
        <div className="empty-state">
          <p>Liste des dépenses — Jalon 13</p>
        </div>
      </div>
    </>
  )
}
