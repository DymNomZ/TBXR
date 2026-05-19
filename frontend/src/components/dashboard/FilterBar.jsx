import { Search } from 'lucide-react'
import { useState } from 'react'

export default function FilterBar({ filterableCols = [], onFilterChange, initialFilters = {} }) {
  const [search, setSearch] = useState(initialFilters.search ?? '')

  // Keyed by column.key → selected option string or ''
  const [filters, setFilters] = useState(
    () => Object.fromEntries(filterableCols.map((c) => [c.key, initialFilters[c.key] ?? '']))
  )

  const handleSearchSubmit = (e) => {
    e.preventDefault()
    onFilterChange({ search: search.trim(), ...filters })
  }

  const handleFilterChange = (key, value) => {
    const next = { ...filters, [key]: value }
    setFilters(next)
    onFilterChange({ search: search.trim(), ...next })
  }

  const handleClearAll = () => {
    const cleared = Object.fromEntries(filterableCols.map((c) => [c.key, '']))
    setFilters(cleared)
    setSearch('')
    onFilterChange({ search: '', ...cleared })
  }

  const hasActiveFilters =
    search.trim() !== '' || filterableCols.some((c) => filters[c.key] !== '')

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Search */}
      <form
        onSubmit={handleSearchSubmit}
        className="flex items-center gap-2 bg-white border border-[var(--border)] rounded-xl px-4 py-2.5 w-64 focus-within:border-[var(--accent)] transition-colors shadow-sm"
      >
        <Search size={14} className="text-[var(--text-muted)] shrink-0" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search..."
          className="bg-transparent outline-none flex-1 text-sm placeholder:text-[var(--text-muted)] text-[var(--text)]"
        />
      </form>

      {/* Dynamic filter dropdowns — one per filterable column */}
      {filterableCols.map((col) => (
        <select
          key={col.key}
          value={filters[col.key]}
          onChange={(e) => handleFilterChange(col.key, e.target.value)}
          className="bg-white border border-[var(--border)] rounded-xl px-3 py-2.5 text-sm text-[var(--text)] shadow-sm cursor-pointer focus:outline-none focus:border-[var(--accent)] transition-colors"
        >
          <option value="">All {col.label ?? col.header}</option>
          {col.filterOptions.map((opt) => (
            <option key={opt} value={opt}>{opt}</option>
          ))}
        </select>
      ))}

      {/* Clear all */}
      {hasActiveFilters && (
        <button
          onClick={handleClearAll}
          className="text-sm text-[var(--text-muted)] hover:text-[var(--text)] underline underline-offset-2 transition-colors"
        >
          Clear Filters
        </button>
      )}
    </div>
  )
}