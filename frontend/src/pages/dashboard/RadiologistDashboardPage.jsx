import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import AppLayout from '../../components/layout/AppLayout'
import StatCard from '../../components/ui/StatCard'
import FilterBar from '../../components/dashboard/FilterBar'
import AIScoreLegend from '../../components/ui/AIScoreLegend'
import RadiologistDashboardTable, { QUEUE_COLUMNS } from '../../components/dashboard/RadiologistDashboardTable'

const FILTERABLE_COLS = QUEUE_COLUMNS.filter((c) => c.filterable)
const PAGE_SIZE = 20

export default function RadiologistDashboardPage() {
  const [page, setPage]             = useState(1)
  const [activeFilters, setFilters] = useState({ search: '', status: '', risk_label: 'HIGH' })
  const [records, setRecords]       = useState([])
  const [count, setCount]           = useState(0)
  const [loading, setLoading]       = useState(false)
  const [stats, setStats] = useState({ pendingReview: 0, completed: 0, highRisk: 0, manualReview: 0, total: 0 })

  // Fetch just the count for a given status — reads from paginated `count` field
  const fetchCount = (params) =>
    fetch(`/api/imaging/queue/?${new URLSearchParams(params)}`, {
      credentials: 'include',
    })
      .then((r) => r.json())
      .then((d) => d.count ?? 0)
      .catch(() => 0)

  // ── Fetch stat counts (parallel, independent of current filter)
  useEffect(() => {
    Promise.all([
      fetchCount({ status: 'AI_REVIEWED' }),
      fetchCount({ status: 'COMPLETED' }),
      fetchCount({ risk_label: 'HIGH' }),
      fetchCount({ status: 'MANUAL_REVIEW' }),
      fetchCount({}),
    ]).then(([pendingReview, completed, highRisk, manualReview, total]) => {
      setStats({ pendingReview, completed, highRisk, manualReview, total })
    })
  }, [])  // once on mount — rerun after submit if needed

  useEffect(() => {
    const params = new URLSearchParams({ page })
    if (activeFilters.search) params.set('search', activeFilters.search)
    if (activeFilters.status) params.set('status', activeFilters.status)
    if (activeFilters.risk_label) params.set('risk_label', activeFilters.risk_label)

    setLoading(true)
    fetch(`/api/imaging/queue/?${params}`, { credentials: 'include' })
      .then((r) => r.json())
      .then((data) => {
        setRecords(data.results ?? [])
        setCount(data.count ?? 0)
      })
      .finally(() => setLoading(false))
  }, [page, activeFilters])

  const totalPages = Math.ceil(count / PAGE_SIZE)

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
    setPage(1)
  }

  return (
    <AppLayout>
      <div className="flex flex-col gap-6">
        <div>
          <h1 className="text-2xl font-bold text-[var(--deep-navy)] tracking-tight">
            Radiology Review Queue
          </h1>
          <p className="text-sm text-[var(--text-muted)] mt-1">
            All X-ray records assigned for radiologist review
          </p>
        </div>

        {/* Stat cards */}
        <div className="flex gap-4 flex-wrap">
          <StatCard label="Pending Specialist Review" value={stats.pendingReview} />
          <StatCard label="Manual Review Required" value={stats.manualReview} highlight />
          <StatCard label="Completed" value={stats.completed} />
          <StatCard label="High Risk" value={stats.highRisk} highlight />
          <StatCard label="Total Records" value={stats.total} />
        </div>

        {/* Filter bar — initialFilters seeds the PENDING default visually */}
        <FilterBar
          filterableCols={FILTERABLE_COLS}
          onFilterChange={handleFilterChange}
          initialFilters={activeFilters}
        />

        {loading ? (
          <div className="text-sm text-[var(--text-muted)] py-8 text-center">
            Loading...
          </div>
        ) : (
          <>
            <RadiologistDashboardTable data={records} />
            <AIScoreLegend sortLabel="Sorted by AI score (highest first)" />
          </>
        )}

        {/* Pagination */}
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