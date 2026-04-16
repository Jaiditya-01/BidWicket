import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard, Trophy, Users, UserCircle,
  Swords, Gavel, LogOut, Settings
} from 'lucide-react';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/tournaments', icon: Trophy, label: 'Tournaments' },
  { to: '/teams', icon: Users, label: 'Teams' },
  { to: '/players', icon: UserCircle, label: 'Players' },
  { to: '/matches', icon: Swords, label: 'Matches' },
  { to: '/auctions', icon: Gavel, label: 'Auctions' },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/login'); };

  const initials = user?.full_name
    ?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() ?? 'U';

  const primaryRole = user?.roles?.[0] ?? 'viewer';

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🏏</div>
        <div className="sidebar-logo-text">Bid<span>Wicket</span></div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-label">Main</div>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon size={17} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="user-pill" style={{ marginBottom: '0.5rem' }}>
          <div className="user-avatar">{initials}</div>
          <div className="user-info">
            <div className="user-name truncate">{user?.full_name}</div>
            <div className="user-role">{primaryRole}</div>
          </div>
        </div>
        <button className="nav-item" style={{ width: '100%', color: 'var(--red)' }} onClick={handleLogout}>
          <LogOut size={17} /> Sign out
        </button>
      </div>
    </aside>
  );
}
