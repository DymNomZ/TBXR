import { useEffect, useState } from 'react'
import { X } from 'lucide-react'

export default function Modal({ isOpen, onClose, title, children, noPadding = false, hideClose = false }) {
  const [mounted, setMounted]   = useState(false)
  const [visible, setVisible]   = useState(false)

  useEffect(() => {
    if (isOpen) {
      setMounted(true)
      // Double rAF ensures the browser has painted the initial state
      // before we apply the visible classes, making the transition fire
      requestAnimationFrame(() => requestAnimationFrame(() => setVisible(true)))
    } else {
      setVisible(false)
      // Unmount after transition completes (200ms)
      const t = setTimeout(() => setMounted(false), 200)
      return () => clearTimeout(t)
    }
  }, [isOpen])

  if (!mounted) return null

  return (
    // Backdrop
    <div
      className={`
        fixed inset-0 z-50 flex items-center justify-center px-4
        transition-all duration-200
        ${visible ? 'bg-black/40' : 'bg-black/0'}
      `}
      onClick={onClose}
    >
      {/* Modal card */}
      <div
        className={`
          relative w-full max-w-md bg-white rounded-[28px]
          border border-[var(--border)] shadow-[var(--shadow)]
          transition-all duration-200
          ${visible ? 'opacity-100 scale-100 translate-y-0' : 'opacity-0 scale-95 translate-y-2'}
          ${noPadding ? '' : 'p-8'}
        `}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close button */}
        {!hideClose && (
          <button
            onClick={onClose}
            className="absolute top-5 right-5 w-8 h-8 flex items-center justify-center rounded-xl text-[var(--text-muted)] hover:bg-[var(--surface-soft)] hover:text-[var(--text)] transition-colors cursor-pointer"
          >
            <X size={16} />
          </button>
        )}

        {/* Optional title */}
        {!hideClose && title && (
          <h2 className="text-2xl font-semibold text-[var(--deep-navy)] mb-6 pr-8">
            {title}
          </h2>
        )}
        
        {children}
      </div>
    </div>
  )
}