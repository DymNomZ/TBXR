import {
  LayoutDashboard,
  CalendarDays,
  UserRound,
  Users,
  MessageSquare,
  Settings,
} from 'lucide-react';
import SidebarItem from './SidebarItem';

// ✏️ Add, remove, or reorder items here, nothing else needs to change
const NAV_ITEMS = [
  { label: 'Dashboard',    icon: LayoutDashboard, to: '/dashboard' },
  { label: 'Appointments', icon: CalendarDays,    to: '/appointments' },
  { label: 'Doctor',       icon: UserRound,       to: '/doctors' },
  { label: 'Patients',     icon: Users,           to: '/patients' },
  { label: 'Messages',     icon: MessageSquare,   to: '/messages' },
  { label: 'Settings',     icon: Settings,        to: '/settings' },
];

export default function Sidebar() {
  return (
    <aside className="w-52 shrink-0 min-h-screen bg-white border-r border-[var(--border)] flex flex-col px-3 py-6 gap-1">
      {/* App title */}
      <div className="px-4 mb-6">
        <span className="text-xl font-bold text-[var(--deep-navy)] tracking-tight">
          TB-XR
        </span>
      </div>

      {/* Nav items */}
      <nav className="flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => (
          <SidebarItem key={item.to} {...item} />
        ))}
      </nav>
    </aside>
  );
}