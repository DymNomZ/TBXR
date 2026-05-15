export default function StatCard({ label, value, highlight = false }) {
  return (
    <div
      className={`
        flex flex-col gap-1 px-6 py-5 rounded-2xl border border-[var(--border)] shadow-sm flex-1
        ${highlight
          ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
          : 'bg-white text-[var(--text)]'
        }
      `}
    >
      <span className={`text-3xl font-bold tracking-tight ${highlight ? 'text-white' : 'text-[var(--deep-navy)]'}`}>
        {value ?? '—'}
      </span>
      <span className={`text-sm ${highlight ? 'text-white/80' : 'text-[var(--text-muted)]'}`}>
        {label}
      </span>
    </div>
  )
}