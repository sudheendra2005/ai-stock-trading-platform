import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';
import { getMarketStatus } from '../utils/marketStatus';

const NAV = [
  { path: '/dashboard', label: 'Dashboard', icon: '⊞' },
  { path: '/portfolio', label: 'Holdings', icon: '▤' },
  { path: '/ai-predictions', label: 'AI Predictions', icon: '◈' },
  { path: '/wallet', label: 'Funds', icon: '₹' },
  { path: '/settings', label: 'Settings', icon: '⚙' },
];

const Sidebar = ({ user, logout }) => {
  const loc = useLocation();
  const [status, setStatus] = useState(() => getMarketStatus());

  useEffect(() => {
    const id = window.setInterval(() => setStatus(getMarketStatus()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-text">NexusAI</div>
        <div className="sidebar-logo-tag" style={{ color: status.color }}>
          {status.open ? 'MARKET OPEN' : 'MARKET CLOSED'}
        </div>
      </div>
      <div className="nav-section-label">Menu</div>
      {NAV.map(n => (
        <Link key={n.path} to={n.path} className={`nav-item ${loc.pathname === n.path ? 'active' : ''}`}>
          <span style={{ fontSize: 15 }}>{n.icon}</span>
          <span>{n.label}</span>
        </Link>
      ))}
      <div style={{ marginTop: 'auto', padding: 16, borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>
          <strong style={{ color: 'var(--text-primary)' }}>{user?.username}</strong><br />
          {user?.email}
        </div>
        <button className="btn btn-ghost btn-block" onClick={() => { logout(); window.location.href = '/'; }}>
          Sign Out
        </button>
      </div>
    </aside>
  );
};

const IndexChip = ({ name, value, change }) => (
  <div className="index-chip">
    <span className="index-name">{name}</span>
    <span className={`index-value ${change >= 0 ? 'up' : 'down'}`}>
      {value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
    </span>
    <span className={`index-change ${change >= 0 ? 'up' : 'down'}`}>
      {change >= 0 ? '▲' : '▼'} {Math.abs(change).toFixed(2)}%
    </span>
  </div>
);

const AppShell = ({ children }) => {
  const { user, logout } = useAuth();
  const [indices, setIndices] = useState([
    { name: 'NIFTY 50', value: 23450.10, change: 0.48 },
    { name: 'SENSEX', value: 77150.40, change: 0.52 },
    { name: 'BANK NIFTY', value: 49820.55, change: -0.21 },
  ]);

  useEffect(() => {
    const fetchIndices = async () => {
      try {
        const [n, s, b] = await Promise.all([
          fetch(`${API_BASE}/api/stocks/${encodeURIComponent('^NSEI')}`).then(r => r.json()),
          fetch(`${API_BASE}/api/stocks/${encodeURIComponent('^BSESN')}`).then(r => r.json()),
          fetch(`${API_BASE}/api/stocks/${encodeURIComponent('^NSEBANK')}`).then(r => r.json()),
        ]);
        const toIdx = (d, name) => ({ name, value: d.current_price || 0, change: d.change || 0 });
        setIndices([toIdx(n, 'NIFTY 50'), toIdx(s, 'SENSEX'), toIdx(b, 'BANK NIFTY')]);
      } catch {
        // Keep defaults if the backend is still warming up.
      }
    };
    fetchIndices();
  }, []);

  return (
    <div className="app-layout">
      <Sidebar user={user} logout={logout} />
      <div className="main-content">
        <header className="topbar">
          <div className="badge-live"><span className="dot-live"></span>Live</div>
          {indices.map(idx => <IndexChip key={idx.name} {...idx} />)}
          <div className="topbar-right">
            <div className="user-badge">
              <div className="user-avatar">{user?.username?.[0]?.toUpperCase()}</div>
              <span style={{ fontSize: 12, fontWeight: 500 }}>{user?.username}</span>
            </div>
          </div>
        </header>
        <div className="page-body">
          {children}
        </div>
      </div>
    </div>
  );
};

export default AppShell;
