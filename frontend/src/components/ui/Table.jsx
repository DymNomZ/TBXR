export default function Table({ columns, data, onRowClick }) {
  return (
    <div className="w-full overflow-x-auto">
      <table className="w-full text-sm border-separate border-spacing-0">
        {/* Head */}
        <thead>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className="text-left text-xs font-semibold text-[var(--text-muted)] uppercase tracking-wide px-5 py-3 bg-[var(--bg)] border-b border-[var(--border)] first:rounded-tl-xl last:rounded-tr-xl"
                style={{ width: col.width ?? 'auto' }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>

        {/* Body */}
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={row.id ?? rowIndex}
              onClick={() => onRowClick?.(row)}
              className={`
                border-b border-[var(--border)] transition-colors last:border-none
                ${onRowClick ? 'cursor-pointer hover:bg-[var(--surface-soft)]' : ''}
              `}
            >
              {columns.map((col) => (
                <td key={col.key} className="px-5 py-4 text-[var(--text)]">
                  {/* 👇 Hacks, each column decides how to render itself */}
                  {col.render(row)}
                </td>
              ))}
            </tr>
          ))}

          {/* Empty state */}
          {data.length === 0 && (
            <tr>
              <td
                colSpan={columns.length}
                className="text-center py-16 text-[var(--text-muted)]"
              >
                No records found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}