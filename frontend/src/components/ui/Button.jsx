const VARIANTS = {
  primary:   'bg-[var(--deep-navy)] text-white hover:opacity-90',
  secondary: 'bg-transparent text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-soft)]',
  danger:    'bg-[var(--danger)] text-white hover:opacity-90',
}

const SIZES = {
  sm: 'px-3 py-1.5 text-xs gap-1.5',
  md: 'px-4 py-2.5 text-sm gap-2',
  lg: 'px-6 py-3 text-base gap-2',
}

export default function Button({
  children,
  onClick,
  variant   = 'primary',
  size      = 'md',
  type      = 'button',
  disabled  = false,
  fullWidth = false,
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`
        inline-flex items-center justify-center font-semibold rounded-xl
        transition-all duration-150 cursor-pointer select-none shrink-0
        ${VARIANTS[variant]}
        ${SIZES[size]}
        ${fullWidth ? 'w-full' : ''}
        ${disabled ? 'opacity-40 cursor-not-allowed pointer-events-none' : ''}
      `}
    >
      {children}
    </button>
  )
}