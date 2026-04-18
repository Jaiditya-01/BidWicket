import React, { useEffect, useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Moon, Sun, Menu, X, LogOut, LayoutDashboard, User } from 'lucide-react';
import './Navbar.css';

export function Navbar() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();
  const [isDark, setIsDark] = useState(() => {
    return localStorage.getItem('theme') !== 'light';
  });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.body.classList.remove('light-mode');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.add('light-mode');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark(!isDark);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navLinks = [
    { to: '/', label: 'Overview' },
    { to: '/tournaments', label: 'Tournaments' },
    { to: '/teams', label: 'Teams' },
    { to: '/players', label: 'Players' },
    { to: '/auctions', label: 'Auctions' },
    { to: '/matches', label: 'Matches' },
  ];

  if (hasRole('admin')) {
    navLinks.push({ to: '/admin', label: 'Admin Panel' });
  }

  return (
    <nav className="navbar">
      <div className="navbar-container container">
        <div className="navbar-brand">
          <NavLink to="/" className="navbar-logo">
            <span className="text-primary">Bid</span>Wicket
          </NavLink>
        </div>

        {user ? (
          <>
            <div className="navbar-links desktop-only">
              {navLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                >
                  {link.label}
                </NavLink>
              ))}
            </div>

            <div className="navbar-actions desktop-only">
              <button
                className="btn btn-icon theme-toggle"
                onClick={toggleTheme}
                title="Toggle theme"
              >
                {isDark ? <Sun size={20} /> : <Moon size={20} />}
              </button>

              <div className="user-menu">
                <NavLink to="/profile" className="btn btn-secondary btn-sm nav-profile-link">
                  <User size={16} /> My Profile
                </NavLink>
                <button className="btn btn-outline btn-sm" onClick={handleLogout}>
                  <LogOut size={16} />
                </button>
              </div>
            </div>

            <button
              className="mobile-menu-btn mobile-only"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            >
              {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          </>
        ) : (
          <div className="navbar-actions">
            <button
              className="btn btn-icon theme-toggle"
              onClick={toggleTheme}
              title="Toggle theme"
            >
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
          </div>
        )}
      </div>

      {user && isMobileMenuOpen && (
        <div className="mobile-menu fade-in">
          {navLinks.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) => `mobile-nav-link ${isActive ? 'active' : ''}`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              {link.label}
            </NavLink>
          ))}
          <div className="mobile-menu-divider" />
          <NavLink
            to="/profile"
            className="mobile-nav-link"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            My Profile
          </NavLink>
          <button className="mobile-nav-link text-red" onClick={handleLogout} style={{ border: 'none', background: 'transparent', textAlign: 'left', width: '100%' }}>
            Logout
          </button>
        </div>
      )}
    </nav>
  );
}
