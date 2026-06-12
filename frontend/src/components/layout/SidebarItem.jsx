import { NavLink } from 'react-router-dom';

export default function SidebarItem({ icon: Icon, label, to }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        `flex items-center gap-3 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors cursor-pointer select-none
        ${
          isActive
            ? 'bg-[var(--accent-soft)] text-[var(--accent)]'
            : 'text-[var(--text-muted)] hover:bg-[var(--surface-soft)] hover:text-[var(--text)]'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            size={18}
            className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}
          />
          <span>{label}</span>
        </>
      )}
    </NavLink>
  );
}