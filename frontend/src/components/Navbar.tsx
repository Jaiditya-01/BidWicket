import { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Moon, Sun, LogOut, User } from 'lucide-react';
import './Navbar.css';

export function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(() => localStorage.getItem('theme') !== 'light');

  useEffect(() => {
    if (isDark) {
      document.body.classList.remove('light-mode');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.add('light-mode');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <nav className="navbar">
      <div className="navbar-container container">
        {/* Brand / Logo */}
        <div className="navbar-brand">
          <NavLink to="/" className="navbar-logo">
            <span className="text-primary">Bid</span>Wicket
          </NavLink>
        </div>

        {/* Right-side actions only — navigation is handled by Sidebar */}
        <div className="navbar-actions">
          <button
            className="btn btn-icon theme-toggle"
            onClick={() => setIsDark(d => !d)}
            title="Toggle theme"
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {user && (
            <div className="user-menu">
              <NavLink to="/profile" className="btn btn-secondary btn-sm nav-profile-link">
                <User size={16} /> My Profile
              </NavLink>
              <button
                className="btn btn-outline btn-sm"
                onClick={handleLogout}
                title="Sign out"
              >
                <LogOut size={16} />
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}
