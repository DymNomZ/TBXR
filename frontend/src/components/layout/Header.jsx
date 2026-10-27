import { Bell, Search, ChevronDown, LogOut, CircleUserRound, CheckCheck } from 'lucide-react';
import { useRef, useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

function getCsrfToken() {
  return document.cookie
    .split('; ')
    .find((row) => row.startsWith('csrftoken='))
    ?.split('=')[1] ?? ''
}

function extractCaseIdFromMessage(message = '') {
  const match = message.match(/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/)
  return match ? match[1] : null
}

export default function Header() {
  const { user, logout } = useAuth();
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loadingNotifications, setLoadingNotifications] = useState(false);
  const notificationsRef = useRef(null);
  const userMenuRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!user || !notificationsOpen) return

    const fetchNotifications = async () => {
      setLoadingNotifications(true)
      try {
        const response = await fetch('/api/imaging/notifications/', { credentials: 'include' })
        if (!response.ok) return
        const data = await response.json()
        setNotifications(Array.isArray(data) ? data : [])
      } catch {
        setNotifications([])
      } finally {
        setLoadingNotifications(false)
      }
    }

    fetchNotifications()
  }, [user, notificationsOpen])

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
        setNotificationsOpen(false)
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setUserMenuOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const unreadCount = notifications.filter((item) => !item.read_status).length

  const handleNotificationClick = async (notification) => {
    const caseId = extractCaseIdFromMessage(notification.message)

    if (!notification.read_status) {
      try {
        await fetch(`/api/imaging/notifications/${notification.id}/mark-read/`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'X-CSRFToken': getCsrfToken() },
        })
      } catch {
        // ignore read-state update failure; navigation can still proceed
      }
    }

    setNotifications((prev) => prev.map((item) => (
      item.id === notification.id ? { ...item, read_status: true } : item
    )))

    setNotificationsOpen(false)

    if (caseId && user?.role === 'RADIOLOGIST') {
      navigate(`/radiologist/review/${caseId}`)
      return
    }

    if (caseId && user?.role === 'PHYSICIAN') {
      navigate(`/dashboard/physician?case=${encodeURIComponent(caseId)}`)
      return
    }

    if (user?.role === 'PHYSICIAN') {
      navigate('/dashboard/physician')
      return
    }

    navigate('/dashboard/radiologist')
  }

  // ── Add / remove items here freely ─────────────────────────────────────────
  const menuItems = [
    {
      icon: LogOut,
      label: 'Log out',
      onClick: async () => { await logout(); navigate('/login'); },
      danger: true,
    },
  ];
  // ───────────────────────────────────────────────────────────────────────────

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-[var(--border)] sticky top-0 z-30">
      <div className="flex items-center gap-2 bg-[var(--bg)] border border-[var(--border)] rounded-xl px-4 py-2 w-72 text-sm text-[var(--text-muted)] focus-within:border-[var(--accent)] transition-colors">
        <Search size={15} className="shrink-0 text-[var(--text-muted)]" />
        <input
          type="text"
          placeholder="Search..."
          className="bg-transparent outline-none w-full placeholder:text-[var(--text-muted)] text-[var(--text)]"
        />
      </div>

      <div className="flex items-center gap-3">
        <div className="relative" ref={notificationsRef}>
          <button
            type="button"
            onClick={() => setNotificationsOpen((o) => !o)}
            className="relative w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors"
            aria-label="Open notifications"
          >
            <Bell size={18} className="text-[var(--text-muted)]" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 min-w-4 h-4 px-1 rounded-full bg-[var(--accent)] text-[10px] text-white flex items-center justify-center font-semibold">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {notificationsOpen && (
            <div className="absolute right-0 mt-2 w-[min(92vw,22rem)] bg-white rounded-2xl border border-[var(--border)] shadow-[var(--shadow)] z-50 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-soft)]">
                <div>
                  <p className="text-sm font-semibold text-[var(--deep-navy)]">Notifications</p>
                  <p className="text-[11px] text-[var(--text-muted)]">
                    {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
                  </p>
                </div>
                {unreadCount > 0 && (
                  <button
                    type="button"
                    onClick={async () => {
                      const unread = notifications.filter((item) => !item.read_status)
                      await Promise.all(unread.map((item) => fetch(`/api/imaging/notifications/${item.id}/mark-read/`, {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'X-CSRFToken': getCsrfToken() },
                      }).catch(() => null)))
                      setNotifications((prev) => prev.map((item) => ({ ...item, read_status: true })))
                    }}
                    className="text-[11px] font-medium text-[var(--accent)] hover:text-[var(--deep-navy)]"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto">
                {loadingNotifications ? (
                  <div className="p-4 text-sm text-[var(--text-muted)]">Loading notifications…</div>
                ) : notifications.length === 0 ? (
                  <div className="p-4 text-sm text-[var(--text-muted)]">No notifications yet.</div>
                ) : (
                  notifications.map((notification) => (
                    <button
                      key={notification.id}
                      type="button"
                      onClick={() => handleNotificationClick(notification)}
                      className={`w-full text-left border-b border-[var(--border)] px-4 py-3 transition-colors hover:bg-[var(--surface-soft)] ${
                        notification.read_status ? 'bg-white' : 'bg-[var(--surface-soft)]'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <span className={`mt-1.5 h-2.5 w-2.5 rounded-full ${notification.read_status ? 'bg-transparent border border-[var(--border)]' : 'bg-[var(--accent)]'}`} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-[var(--deep-navy)] leading-5 break-words">{notification.message}</p>
                          <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                            {notification.created_at ? new Date(notification.created_at).toLocaleString() : 'Just now'}
                          </p>
                        </div>
                        {!notification.read_status && (
                          <CheckCheck size={14} className="mt-1 text-[var(--accent)]" />
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="w-px h-6 bg-[var(--border)]" />

        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => setUserMenuOpen((o) => !o)}
            className="flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-[var(--surface-soft)] transition-colors"
          >
            <span className="w-8 h-8 rounded-full bg-[var(--surface-soft)] border border-[var(--border)] flex items-center justify-center" aria-hidden="true">
              <CircleUserRound size={18} className="text-[var(--text-muted)]" />
            </span>
            <ChevronDown
              size={14}
              className={`text-[var(--text-muted)] transition-transform duration-200 ${userMenuOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {userMenuOpen && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl border border-[var(--border)] shadow-[var(--shadow)] py-1.5 z-50">
              <div className="px-4 py-2.5 border-b border-[var(--border)] mb-1">
                <p className="text-sm font-semibold text-[var(--deep-navy)] truncate">
                  {user?.name ?? 'User'}
                </p>
                <p className="text-xs text-[var(--text-muted)] truncate">
                  {user?.email ?? ''}
                </p>
              </div>

              {menuItems.map((item, i) =>
                item.divider ? (
                  <div key={i} className="my-1 border-t border-[var(--border)]" />
                ) : (
                  <button
                    key={i}
                    onClick={() => { item.onClick(); setUserMenuOpen(false); }}
                    className={`
                      w-full flex items-center gap-3 px-4 py-2 text-sm transition-colors
                      ${item.danger
                        ? 'text-[var(--danger)] hover:bg-red-50'
                        : 'text-[var(--text)] hover:bg-[var(--surface-soft)]'}
                    `}
                  >
                    <item.icon size={15} className="shrink-0" />
                    {item.label}
                  </button>
                )
              )}
            </div>
          )}
        </div>
      </div>
    </header>
  );
}