import Topbar from '../components/layout/Topbar'

export default function DashboardPage() {
  return (
    <>
      <Topbar title="Tableau de bord" />
      <div className="content">
        <div className="empty-state">
          <p>Tableau de bord — Jalon 12</p>
        </div>
      </div>
    </>
  )
}
