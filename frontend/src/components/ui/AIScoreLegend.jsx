const ITEMS = [
  { color: 'bg-red-500',    label: 'High Priority',   range: '≥70%'    },
  { color: 'bg-orange-400', label: 'Medium Priority', range: '40–69%'  },
  { color: 'bg-green-500',  label: 'Low Priority',    range: '<40%'    },
]

// sortLabel — optional right-side annotation, e.g. "Sorted by AI score (highest first)"
export default function AIScoreLegend({ sortLabel }) {
  return (
    <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
      <div className="flex items-center gap-5">
        {ITEMS.map((item) => (
          <span key={item.label} className="flex items-center gap-1.5">
            <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${item.color}`} />
            {item.label} ({item.range})
          </span>
        ))}
      </div>
      {sortLabel && <span>{sortLabel}</span>}
    </div>
  )
}