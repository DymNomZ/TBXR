function SelectField({ id, label, value, onChange, options, error }) {
  return (
    <label className="block text-sm font-medium text-slate-700" htmlFor={id}>
      {label}
      <select
        id={id}
        name={id}
        value={value}
        onChange={onChange}
        required
        className={`mt-3 w-full rounded-3xl border bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-4 focus:ring-slate-100 ${
          error
            ? 'border-red-400 focus:border-red-400'
            : 'border-slate-200 focus:border-slate-indigo-500'
        }`}
      >
        <option value="" disabled>
          Select an option
        </option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <span className="mt-1.5 block px-2 text-xs text-red-600">{error}</span>
      )}
    </label>
  )
}

export default SelectField