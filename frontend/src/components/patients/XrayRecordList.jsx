import { Clock } from 'lucide-react';
import StatusBadge from '../ui/StatusBadge'

function XrayRecordItem({ record }) {

  return (
    <div className="flex flex-col gap-1.5 p-4 rounded-xl border border-[var(--border)] hover:bg-[var(--surface-soft)] transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-[var(--deep-navy)] font-mono">
          {record.transaction_id}
        </span>
        <StatusBadge status={record.status} />
      </div>

      <div className="flex items-center justify-between text-xs text-[var(--text-muted)]">
        <span>{record.date}</span>
        {/* <span>{record.view_type}</span> */}
      </div>

      {record.reviewing_doctor && (
        <div className="text-xs text-[var(--text-muted)] text-right">
          {/* {record.reviewing_doctor} */}
        </div>
      )}
    </div>
  );
}

export default function XrayRecordList({ records = [] }) {
  return (
    <div className="bg-white rounded-2xl border border-[var(--border)] shadow-sm p-6 flex flex-col gap-4">
      {/* Card header */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-full bg-[var(--accent-soft)] flex items-center justify-center">
          <Clock size={16} className="text-[var(--accent)]" />
        </div>
        <h2 className="text-base font-bold text-[var(--deep-navy)]">X-Ray Record History</h2>
        {records.length > 0 && (
          <span className="ml-auto text-xs font-semibold bg-[var(--accent-soft)] text-[var(--accent)] px-2.5 py-1 rounded-full">
            {records.length} record{records.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Records */}
      {records.length > 0 ? (
        <div className="flex flex-col gap-2">
          {records.map((record) => (
            <XrayRecordItem key={record.transaction_id} record={record} />
          ))}
        </div>
      ) : (
        // Empty state — expected initially per the task
        <div className="flex flex-col items-center justify-center py-12 text-center gap-2">
          <div className="w-12 h-12 rounded-full bg-[var(--surface-soft)] flex items-center justify-center mb-1">
            <Clock size={22} className="text-[var(--text-muted)]" />
          </div>
          <p className="text-sm font-medium text-[var(--text)]">No records yet</p>
          <p className="text-xs text-[var(--text-muted)]">
            X-ray records will appear here once uploads come in.
          </p>
        </div>
      )}
    </div>
  );
}