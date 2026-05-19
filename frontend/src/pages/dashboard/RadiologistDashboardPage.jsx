import { useState, useEffect } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import AppLayout from '../../components/layout/AppLayout'
import StatCard from '../../components/ui/StatCard'
import FilterBar from '../../components/dashboard/FilterBar'
import RadiologistDashboardTable, { QUEUE_COLUMNS } from '../../components/dashboard/RadiologistDashboardTable'

const FILTERABLE_COLS = QUEUE_COLUMNS.filter((c) => c.filterable)
const PAGE_SIZE = 20

// Fetch just the count for a given status — reads from paginated `count` field
const fetchStatusCount = (status) =>
  fetch(`/api/imaging/queue/?status=${status}`, { credentials: 'include' })
    .then((r) => r.json())
    .then((d) => d.count ?? 0)
    .catch(() => 0)

export default function RadiologistDashboardPage() {
  const navigate = useNavigate()
  const [page, setPage]             = useState(1)
  const [activeFilters, setFilters] = useState({ search: '', status: 'PENDING' })
  const [records, setRecords]       = useState([])
  const [count, setCount]           = useState(0)
  const [loading, setLoading]       = useState(false)
  const [stats, setStats] = useState({ pending: 0, inReview: 0, completed: 0, total: 0 })

  // ── Fetch stat counts (parallel, independent of current filter)
  useEffect(() => {
    Promise.all([
      fetchStatusCount('PENDING'),
      fetchStatusCount('IN_REVIEW'),
      fetchStatusCount('COMPLETED'),
    ]).then(([pending, inReview, completed]) => {
      setStats({ pending, inReview, completed, total: pending + inReview + completed })
    })
  }, [])  // once on mount — rerun after submit if needed

  useEffect(() => {
    const params = new URLSearchParams({ page })
    if (activeFilters.search) params.set('search', activeFilters.search)
    if (activeFilters.status) params.set('status', activeFilters.status)

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
        <div className="flex gap-4">
          <StatCard label="Pending Review" value={stats.pending}   />
          <StatCard label="In Review"      value={stats.inReview}  />
          <StatCard label="Completed"      value={stats.completed} />
          <StatCard label="Total Records"  value={stats.total} highlight />
        </div>

        {/* Filter bar — initialFilters seeds the PENDING default visually */}
        <FilterBar
          filterableCols={FILTERABLE_COLS}
          onFilterChange={handleFilterChange}
          initialFilters={{ status: 'PENDING' }}
        />

        {loading ? (
          <div className="text-sm text-[var(--text-muted)] py-8 text-center">
            Loading...
          </div>
        ) : (
          <RadiologistDashboardTable data={records} />
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