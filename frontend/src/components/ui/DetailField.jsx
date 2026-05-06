export default function DetailField({ label, value, mono = false, last = false }) {
  return (
    <div className={`flex items-center justify-between py-3 ${!last ? 'border-b border-[var(--border)]' : ''}`}>
      <span className="text-sm text-[var(--text-muted)]">{label}</span>
      {mono ? (
        <span className="text-xs font-medium font-mono text-[var(--text)] bg-[var(--surface-soft)] px-2 py-1 rounded-md text-right break-all">
          {value}
        </span>
      ) : (
        <span className="text-sm font-medium text-[var(--text)] text-right">{value ?? '—'}</span>
      )}
    </div>
  )
}