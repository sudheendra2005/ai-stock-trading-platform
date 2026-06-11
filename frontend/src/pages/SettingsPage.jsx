import React, { useState, useEffect } from 'react';
import AppShell from '../components/AppShell';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { API_BASE } from '../config/api';
import { ACCENT_OPTIONS, applyAccentTheme } from '../utils/theme';

const SettingsPage = () => {
  const { user, logout } = useAuth();
  const [defaultSymbol, setDefaultSymbol] = useState(localStorage.getItem('default_symbol') || 'RELIANCE.NS');
  const [defaultQty, setDefaultQty] = useState(localStorage.getItem('default_quantity') || '1');
  const [chartStyle, setChartStyle] = useState(localStorage.getItem('chart_style') || 'candlestick');
  const [soundAlerts, setSoundAlerts] = useState(localStorage.getItem('sound_alerts') !== 'false');
  const [accentColor, setAccentColor] = useState(localStorage.getItem('accent_color') || 'green');
  
  const [msg, setMsg] = useState(null);
  const [resetting, setResetting] = useState(false);
  const [virtualBalance, setVirtualBalance] = useState(user?.balance ?? 100000.0);

  const token = localStorage.getItem('token');
  const base = API_BASE;

  useEffect(() => {
    if (user) {
      setVirtualBalance(user.balance ?? 100000.0);
    }
  }, [user]);

  useEffect(() => {
    applyAccentTheme(accentColor);
  }, [accentColor]);

  const handleSaveSettings = (e) => {
    e.preventDefault();
    localStorage.setItem('default_symbol', defaultSymbol.toUpperCase());
    localStorage.setItem('default_quantity', defaultQty);
    localStorage.setItem('chart_style', chartStyle);
    localStorage.setItem('sound_alerts', soundAlerts.toString());
    localStorage.setItem('accent_color', accentColor);
    
    applyAccentTheme(accentColor);

    setMsg({ type: 'success', text: 'Customization settings updated successfully!' });
    setTimeout(() => setMsg(null), 3000);
  };

  const handleResetBalance = async () => {
    if (!window.confirm('Are you sure you want to reset your paper trading balance back to ₹1,00,000.00? This will restore your funds but keep your transaction history.')) {
      return;
    }
    setResetting(true);
    setMsg(null);
    try {
      const response = await axios.post(`${base}/api/auth/reset-balance`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setVirtualBalance(response.data.balance);
      
      // Update local storage/context user balance if applicable
      if (user) {
        user.balance = response.data.balance;
      }
      
      setMsg({ type: 'success', text: 'Simulated balance successfully restored to ₹1,00,000.00!' });
    } catch (error) {
      setMsg({ type: 'error', text: error.response?.data?.detail || 'Failed to reset balance' });
    } finally {
      setResetting(false);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  return (
    <AppShell>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Customization &amp; Settings</h1>
        <div className="text-muted text-xs" style={{ marginTop: 4 }}>Tailor your AI trading terminal interface and manage your paper trade assets</div>
      </div>

      {msg && (
        <div style={{
          padding: '12px 14px', marginBottom: 16, borderRadius: 6, fontSize: 13,
          background: msg.type === 'success' ? 'var(--green-dim)' : 'var(--red-dim)',
          color: msg.type === 'success' ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${msg.type === 'success' ? 'rgba(0,179,134,0.3)' : 'rgba(224,80,80,0.3)'}`,
          maxWidth: 600
        }}>
          {msg.text}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 20, maxWidth: 1000 }}>
        {/* Left Side - Customization Form */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Terminal Personalization</span>
              <span className="tag tag-blue">UI Preferences</span>
            </div>
            <div className="card-body">
              <form onSubmit={handleSaveSettings}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                  <div className="form-group">
                    <label className="form-label">Default Trading Asset</label>
                    <input 
                      className="form-input" 
                      value={defaultSymbol} 
                      onChange={e => setDefaultSymbol(e.target.value)} 
                      placeholder="e.g. RELIANCE.NS" 
                    />
                    <span className="text-xs text-muted" style={{ marginTop: 4, display: 'block' }}>Symbol preloaded in search</span>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Default Quantity</label>
                    <input 
                      className="form-input" 
                      type="number" 
                      min="1"
                      value={defaultQty} 
                      onChange={e => setDefaultQty(e.target.value)} 
                    />
                    <span className="text-xs text-muted" style={{ marginTop: 4, display: 'block' }}>Initial quantity on trade panel</span>
                  </div>
                </div>

                <div className="form-group" style={{ marginBottom: 16 }}>
                  <label className="form-label">Terminal Primary Accent</label>
                  <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
                    {ACCENT_OPTIONS.map(c => (
                      <button
                        key={c.id}
                        type="button"
                        onClick={() => setAccentColor(c.id)}
                        style={{
                          display: 'flex', alignItems: 'center', gap: 6,
                          padding: '6px 12px', borderRadius: 4, cursor: 'pointer',
                          background: 'var(--bg-main)', border: accentColor === c.id ? `2px solid ${c.color}` : '1px solid var(--border)',
                          color: accentColor === c.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                          fontSize: 12, fontWeight: 600
                        }}
                      >
                        <span style={{ width: 8, height: 8, borderRadius: '50%', background: c.color }}></span>
                        {c.name}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
                  <div className="form-group">
                    <label className="form-label">Chart Preference</label>
                    <select 
                      className="form-input" 
                      value={chartStyle} 
                      onChange={e => setChartStyle(e.target.value)}
                    >
                      <option value="candlestick">Candlestick Charts</option>
                      <option value="line">Line Charts</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label className="form-label">Audio Alerts</label>
                    <div style={{ display: 'flex', alignItems: 'center', height: 38 }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
                        <input 
                          type="checkbox" 
                          checked={soundAlerts} 
                          onChange={e => setSoundAlerts(e.target.checked)}
                          style={{ accentColor: 'var(--blue)', width: 16, height: 16 }}
                        />
                        Enable Trade Exec Sound
                      </label>
                    </div>
                  </div>
                </div>

                <button type="submit" className="btn btn-primary" style={{ padding: '9px 24px', fontSize: 13 }}>
                  Save Customizations
                </button>
              </form>
            </div>
          </div>
        </div>

        {/* Right Side - Account & Balance Management */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <span className="card-title">Profile &amp; Credentials</span>
              <span className="tag tag-green">Active Session</span>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
                <div style={{
                  width: 48, height: 48, borderRadius: '50%',
                  background: 'var(--blue-dim)', color: 'var(--blue)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 20, fontWeight: 700
                }}>
                  {user?.username?.[0]?.toUpperCase()}
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{user?.username}</div>
                  <div className="text-xs text-muted" style={{ marginTop: 2 }}>{user?.email}</div>
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 12, padding: '12px 14px', background: 'var(--bg-main)', borderRadius: 6, border: '1px solid var(--border)', marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Member Since</span>
                  <span style={{ fontWeight: 600 }}>{user?.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }) : 'May 2026'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Trading System</span>
                  <span style={{ fontWeight: 600, color: 'var(--green)' }}>NSE · BSE · Live Simulation</span>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">Simulated Funds Control</span>
              <span className="tag tag-red">Emergency Reset</span>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                <span className="text-xs text-secondary" style={{ fontWeight: 600, textTransform: 'uppercase' }}>Paper Trading Balance</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: 'var(--green)' }}>
                  ₹{virtualBalance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </span>
              </div>
              <p style={{ color: 'var(--text-secondary)', fontSize: 12, lineHeight: 1.6, marginBottom: 16 }}>
                Depleted your capital or want a fresh start? Resetting your simulated funds will restore your virtual trading wallet to standard ₹1,00,000.00 instantly.
              </p>
              <button 
                type="button" 
                onClick={handleResetBalance} 
                disabled={resetting}
                className="btn btn-sell btn-block" 
                style={{ padding: '10px 0', fontSize: 13, fontWeight: 700 }}
              >
                {resetting ? 'Resetting Terminal...' : '🔄 Restore Funds to ₹1,00,000.00'}
              </button>
            </div>
          </div>

          <button onClick={() => { logout(); window.location.href = '/'; }} className="btn btn-ghost" style={{ padding: '10px 24px', alignSelf: 'flex-start' }}>
            🚪 Sign Out of Terminal
          </button>
        </div>
      </div>
    </AppShell>
  );
};

export default SettingsPage;
