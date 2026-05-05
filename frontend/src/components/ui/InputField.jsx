function InputField({
  id,
  label,
  type = 'text',
  value,
  onChange,
  placeholder,
  autoComplete,
  error
}) {
  return (
    <label className="block text-sm font-medium text-slate-700" htmlFor={id}>
      {label}
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        onChange={onChange}
        required
        placeholder={placeholder}
        autoComplete={autoComplete}
        className={`mt-3 w-full rounded-3xl border bg-slate-50 px-4 py-3 text-sm text-slate-900 outline-none transition focus:ring-4 focus:ring-slate-100 ${
          error
            ? 'border-red-400 focus:border-red-400'
            : 'border-slate-200 focus:border-slate-indigo-500'
        }`}
      />
      {error && (
        <span className="mt-1.5 block px-2 text-xs text-red-600">{error}</span>
      )}
    </label>
  )
}

export default InputField
