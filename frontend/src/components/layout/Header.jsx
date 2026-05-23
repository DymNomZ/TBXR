import { Bell, MessageSquare, Search, ChevronDown, LogOut, User, Settings } from 'lucide-react';
import { useRef, useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';

export default function Header() {
  const { user, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Close on outside click
  useEffect(() => {
    if (!dropdownOpen) return;
    const handler = (e) => {
      if (!dropdownRef.current?.contains(e.target)) setDropdownOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [dropdownOpen]);

  // ── Add / remove items here freely ─────────────────────────────────────────
  const menuItems = [
    {
      icon: User,
      label: 'My Profile',
      onClick: () => { /* TODO */ },
    },
    {
      icon: Settings,
      label: 'Settings',
      onClick: () => { /* TODO */ },
    },
    { divider: true },
    {
      icon: LogOut,
      label: 'Log out',
      onClick: logout,
      danger: true,
    },
  ];
  // ───────────────────────────────────────────────────────────────────────────

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-[var(--border)] sticky top-0 z-30">
      {/* Search */}
      <div className="flex items-center gap-2 bg-[var(--bg)] border border-[var(--border)] rounded-xl px-4 py-2 w-72 text-sm text-[var(--text-muted)] focus-within:border-[var(--accent)] transition-colors">
        <Search size={15} className="shrink-0 text-[var(--text-muted)]" />
        <input
          type="text"
          placeholder="Search..."
          className="bg-transparent outline-none w-full placeholder:text-[var(--text-muted)] text-[var(--text)]"
        />
      </div>

      {/* Right actions */}
      <div className="flex items-center gap-3">
        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors">
          <Bell size={18} className="text-[var(--text-muted)]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--accent)]" />
        </button>
        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors">
          <MessageSquare size={18} className="text-[var(--text-muted)]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--danger)]" />
        </button>

        <div className="w-px h-6 bg-[var(--border)]" />

        {/* Avatar + dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={() => setDropdownOpen((o) => !o)}
            className="flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-[var(--surface-soft)] transition-colors"
          >
            <img
              src={user?.avatar ?? `https://i.pravatar.cc/150?img=47`}
              alt={user?.name ?? 'User'}
              className="w-8 h-8 rounded-full object-cover"
            />
            <ChevronDown
              size={14}
              className={`text-[var(--text-muted)] transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
            />
          </button>

          {/* Dropdown */}
          {dropdownOpen && (
            <div className="absolute right-0 mt-2 w-52 bg-white rounded-2xl border border-[var(--border)] shadow-[var(--shadow)] py-1.5 z-50">
              {/* User info header */}
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
                    onClick={() => { item.onClick(); setDropdownOpen(false); }}
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