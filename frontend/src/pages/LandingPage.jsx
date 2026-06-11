import React from 'react';
import { Link, useNavigate } from 'react-router-dom';

const LandingPage = () => {
  const navigate = useNavigate();
  return (
    <div style={{ minHeight: '100vh', background: '#0d0d0d', display: 'flex', flexDirection: 'column' }}>
      {/* Nav */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 48px', borderBottom: '1px solid #1e1e1e' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, background: '#00b386', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 14, color: '#000' }}>N</div>
          <span style={{ fontWeight: 700, fontSize: 16 }}>NexusAI</span>
          <span style={{ fontSize: 10, color: '#00b386', fontWeight: 600, marginLeft: 4, border: '1px solid rgba(0,179,134,0.3)', padding: '2px 6px', borderRadius: 3 }}>BETA</span>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
          <Link to="/login" style={{ color: '#a0a0a0', textDecoration: 'none', fontSize: 13, fontWeight: 500 }}>Login</Link>
          <button onClick={() => navigate('/register')} style={{ background: '#00b386', color: '#000', border: 'none', padding: '8px 20px', borderRadius: 4, fontWeight: 600, fontSize: 13, cursor: 'pointer' }}>
            Open Free Account
          </button>
        </div>
      </nav>

      {/* Hero */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '80px 48px', textAlign: 'center' }}>
        <div style={{ display: 'inline-block', background: 'rgba(0,179,134,0.1)', border: '1px solid rgba(0,179,134,0.25)', color: '#00b386', padding: '5px 14px', borderRadius: 3, fontSize: 11, fontWeight: 600, letterSpacing: 1, textTransform: 'uppercase', marginBottom: 28 }}>
          AI-Powered Stock Analysis Platform
        </div>

        <h1 style={{ fontSize: 52, fontWeight: 800, lineHeight: 1.15, maxWidth: 680, marginBottom: 20 }}>
          Invest smarter with <span style={{ color: '#00b386' }}>AI predictions</span>
        </h1>

        <p style={{ fontSize: 16, color: '#7a7a7a', maxWidth: 520, lineHeight: 1.7, marginBottom: 40 }}>
          Get real-time NSE/BSE stock data, AI-generated buy/sell signals, and practice trading with ₹1,00,000 virtual money — zero risk.
        </p>

        <div style={{ display: 'flex', gap: 12 }}>
          <button onClick={() => navigate('/register')} style={{ background: '#00b386', color: '#000', border: 'none', padding: '13px 32px', borderRadius: 4, fontWeight: 700, fontSize: 15, cursor: 'pointer' }}>
            Start Free Paper Trading →
          </button>
          <button onClick={() => navigate('/login')} style={{ background: 'transparent', color: '#a0a0a0', border: '1px solid #2e2e2e', padding: '13px 28px', borderRadius: 4, fontWeight: 600, fontSize: 14, cursor: 'pointer' }}>
            Sign In
          </button>
        </div>

        {/* Feature pills */}
        <div style={{ display: 'flex', gap: 10, marginTop: 48, flexWrap: 'wrap', justifyContent: 'center' }}>
          {['✓ NSE / BSE Live Data', '✓ AI Buy/Sell Signals', '✓ ₹1L Virtual Wallet', '✓ Technical Analysis', '✓ No Real Money'].map(f => (
            <span key={f} style={{ background: '#1a1a1a', border: '1px solid #2e2e2e', padding: '6px 14px', borderRadius: 3, fontSize: 12, color: '#a0a0a0', fontWeight: 500 }}>{f}</span>
          ))}
        </div>
      </div>

      {/* Stats bar */}
      <div style={{ borderTop: '1px solid #1e1e1e', display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', textAlign: 'center', padding: '24px 48px' }}>
        {[['₹1,00,000', 'Virtual Trading Balance'], ['6 Stocks', 'Live Market Coverage'], ['AI Engine', 'Neural Predictions']].map(([v, l]) => (
          <div key={l}>
            <div style={{ fontSize: 22, fontWeight: 700, color: '#f0f0f0', marginBottom: 4 }}>{v}</div>
            <div style={{ fontSize: 12, color: '#5a5a5a' }}>{l}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default LandingPage;
