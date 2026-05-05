import { Bell, MessageSquare, Search, ChevronDown } from 'lucide-react';

// Swap this with your auth hook later
const MOCK_USER = {
  name: 'Dr. Anna Reyes',
  avatar: 'https://i.pravatar.cc/150?img=47',
};

export default function Header() {
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
        {/* Notification bell */}
        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors">
          <Bell size={18} className="text-[var(--text-muted)]" />
          {/* Badge — swap count with real data later */}
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--accent)]" />
        </button>

        {/* Messages */}
        <button className="relative w-9 h-9 flex items-center justify-center rounded-xl hover:bg-[var(--surface-soft)] transition-colors">
          <MessageSquare size={18} className="text-[var(--text-muted)]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--danger)]" />
        </button>

        {/* Divider */}
        <div className="w-px h-6 bg-[var(--border)]" />

        {/* User avatar */}
        <button className="flex items-center gap-2 rounded-xl px-2 py-1 hover:bg-[var(--surface-soft)] transition-colors">
          <img
            src={MOCK_USER.avatar}
            alt={MOCK_USER.name}
            className="w-8 h-8 rounded-full object-cover"
          />
          <ChevronDown size={14} className="text-[var(--text-muted)]" />
        </button>
      </div>
    </header>
  );
}