import Topbar from '../components/layout/Topbar'

export default function CategoriesPage() {
  return (
    <>
      <Topbar title="Catégories" />
      <div className="content">
        <div className="empty-state">
          <p>Gestion des catégories — Jalon 15</p>
        </div>
      </div>
    </>
  )
}
