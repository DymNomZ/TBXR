import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import AppLayout from '../../components/layout/AppLayout'
import StatCard from '../../components/ui/StatCard'
import FilterBar from '../../components/dashboard/FilterBar'
import AIScoreLegend from '../../components/ui/AIScoreLegend'
import TechnologistDashboardTable, { DASHBOARD_COLUMNS } from '../../components/dashboard/TechnologistDashboardTable'

// Pull only the filterable columns to pass to FilterBar
const FILTERABLE_COLS = DASHBOARD_COLUMNS.filter((c) => c.filterable)
const PAGE_SIZE = 20

export default function TechDashboardPage() {
  const [page, setPage]             = useState(1)
  const [activeFilters, setFilters] = useState({ search: '', status: '' })
  const [records, setRecords]       = useState([])
  const [count, setCount]           = useState(0)
  const [loading, setLoading]       = useState(false)

  useEffect(() => {
    const params = new URLSearchParams({ page })

    if (activeFilters.search) params.set('search', activeFilters.search)
    if (activeFilters.status) params.set('status', activeFilters.status)

    setLoading(true)
    fetch(`/api/imaging/dashboard/technologist/?${params}`, {
      credentials: 'include',
    })
      .then((r) => r.json())
      .then((data) => {
        setRecords(data.results ?? [])
        setCount(data.count ?? 0)
      })
      .finally(() => setLoading(false))
  }, [page, activeFilters])  // re-runs whenever page or filters change

  const totalPages = Math.ceil(count / PAGE_SIZE)

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
    setPage(1)  // reset to page 1 on every filter/search change
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
            X-Ray Review Queue
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            Showing all transactions assigned to your account
          </p>
        </div>

        {/* Stat cards — wire to a real endpoint later */}
        <div className="flex gap-4">
          <StatCard label="Pending Review"        value={records.filter(r => r.status === 'PENDING').length}   />
          <StatCard label="In Progress"           value={records.filter(r => r.status === 'IN_REVIEW').length} />
          <StatCard label="Completed (This Page)" value={records.filter(r => r.status === 'COMPLETED').length} />
          <StatCard label="Total Records"         value={count} highlight />
        </div>

        <FilterBar
          filterableCols={FILTERABLE_COLS}
          onFilterChange={handleFilterChange}
        />

        {loading ? (
          <div className="text-sm text-[var(--text-muted)] py-8 text-center">Loading...</div>
        ) : (
          <>
            <TechnologistDashboardTable data={records} />
            <AIScoreLegend sortLabel="Sorted by AI score (highest first)" />
          </>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between text-sm text-[var(--text-muted)]">
            <span>
              Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, count)} of {count} records
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="flex items-center gap-1 px-3 py-2 rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={15} /> Previous
              </button>
              <span className="px-3 py-2 font-medium text-[var(--text)]">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="flex items-center gap-1 px-3 py-2 rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Next <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  )
}