export const AI_DISCLAIMER_TEXT = 'AI-generated assessments are assistive only and are not a definitive diagnosis. Final clinical decisions remain with licensed medical professionals.'

export default function AIDisclaimer({ className = '' }) {
  return (
    <div
      className={`w-full rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm ${className}`}
      role="note"
      aria-live="polite"
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-base" aria-hidden="true">⚠️</span>
        <p className="leading-relaxed">{AI_DISCLAIMER_TEXT}</p>
      </div>
    </div>
  )
}
