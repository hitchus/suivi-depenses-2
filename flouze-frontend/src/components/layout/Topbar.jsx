export default function Topbar({ title, actions }) {
  return (
    <header style={styles.topbar}>
      <span style={styles.title}>{title}</span>
      {actions && <div style={styles.actions}>{actions}</div>}
    </header>
  )
}

const styles = {
  topbar: {
    height: 56, background: 'var(--surface)', borderBottom: '1px solid var(--border)',
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '0 24px', flexShrink: 0,
  },
  title:   { fontSize: 15, fontWeight: 500 },
  actions: { display: 'flex', alignItems: 'center', gap: 8 },
}
