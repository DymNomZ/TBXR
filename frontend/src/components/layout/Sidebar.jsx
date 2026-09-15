import { useAuth } from '../../context/AuthContext'
import {
  LayoutDashboard,
  BarChart3,
  CalendarDays,
  UserRound,
  Users,
  MessageSquare,
  Settings,
} from 'lucide-react';
import SidebarItem from './SidebarItem';

export default function Sidebar() {
  const { user, ROLE_DASHBOARD } = useAuth()
  const canViewAnalytics = user?.role === 'RADIOLOGIST' || user?.role === 'PHYSICIAN'

  // ✏️ Add, remove, or reorder items here, nothing else needs to change
  const NAV_ITEMS = [
    { label: 'Dashboard', icon: LayoutDashboard, to: ROLE_DASHBOARD[user?.role] ?? '/dashboard' },
    ...(canViewAnalytics ? [{ label: 'Analytics', icon: BarChart3, to: '/dashboard/analytics' }] : []),
    { label: 'Appointments', icon: CalendarDays,    to: '/appointments' },
    { label: 'Doctor',       icon: UserRound,       to: '/doctors' },
    { label: 'Patients',     icon: Users,           to: '/patients' },
    { label: 'Messages',     icon: MessageSquare,   to: '/messages' },
    { label: 'Settings',     icon: Settings,        to: '/settings' },
  ];

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