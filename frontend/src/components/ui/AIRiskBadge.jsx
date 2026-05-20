const STYLES = {
  HIGH:     'bg-red-100 text-red-700',
  MODERATE: 'bg-orange-100 text-orange-700',
  LOW:      'bg-green-100 text-green-700',
}

const DEFAULT = 'bg-gray-100 text-gray-500'

export default function AIRiskBadge({ label, score }) {
  const style   = STYLES[label] ?? DEFAULT
  const percent = score != null ? `${Math.round(score * 100)}%` : null

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${style}`}>
      {label}
      {percent && (
        <>
          <span className="opacity-40">·</span>
          {percent}
        </>
      )}
    </span>
  )
}