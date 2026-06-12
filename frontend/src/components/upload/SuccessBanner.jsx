export default function SuccessBanner({ title, subtitle }) {
  return (
    <div className="bg-[var(--deep-navy)] px-6 py-5 flex items-start gap-4">
      <div className="w-12 h-12 rounded-full bg-[var(--accent)] flex items-center justify-center shrink-0">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="#ffffff"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </div>
      <div>
        <p className="text-base font-semibold text-white mb-1">{title}</p>
        <p className="text-sm text-white/60 leading-relaxed">{subtitle}</p>
      </div>
    </div>
  )
}
 