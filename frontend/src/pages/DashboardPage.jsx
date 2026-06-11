import React, { useState, useEffect } from 'react';
import AppShell from '../components/AppShell';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';
import { getMarketStatus as getLiveMarketStatus } from '../utils/marketStatus';

const WATCHLIST = [
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries', sector: 'Energy' },
  { symbol: 'TCS.NS', name: 'Tata Consultancy Services', sector: 'IT' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank', sector: 'Banking' },
  { symbol: 'INFY.NS', name: 'Infosys', sector: 'IT' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank', sector: 'Banking' },
  { symbol: 'AAPL', name: 'Apple Inc.', sector: 'Tech' },
];

const DashboardPage = () => {
  const { user } = useAuth();
  const [stocks, setStocks] = useState([]);
  const [wallet, setWallet] = useState({ balance: 100000 });
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  // Trade form state
  const [tradeSymbol, setTradeSymbol] = useState(localStorage.getItem('default_symbol') || 'RELIANCE.NS');
  const [tradeQty, setTradeQty] = useState(Number(localStorage.getItem('default_quantity') || 1));
  const [tradeType, setTradeType] = useState('market');
  const [trading, setTrading] = useState(false);
  const [tradeMsg, setTradeMsg] = useState(null); // {type: 'success'|'error', text}

  // Search state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);
  const [searching, setSearching] = useState(false);
  const [marketStatus, setMarketStatus] = useState(() => getLiveMarketStatus());

  const token = localStorage.getItem('token');
  const base = API_BASE;

  const fetchData = async () => {
    try {
      const [dashRes, walletRes, portRes, txRes] = await Promise.all([
        fetch(`${base}/api/trading/dashboard`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${base}/api/trading/wallet`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${base}/api/trading/portfolio`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch(`${base}/api/trading/transactions`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      ]);
      
      setStocks(dashRes.trending_stocks || []);
      setWallet(walletRes);
      setTransactions(txRes || []);
    } catch (e) { 
      console.error('Dashboard fetch error:', e); 
    }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchData(); }, []);

  useEffect(() => {
    const id = window.setInterval(() => setMarketStatus(getLiveMarketStatus()), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setSearching(true); setSearchResult(null);
    try {
      const encoded = encodeURIComponent(searchQuery.trim().toUpperCase());
      const r = await fetch(`${base}/api/trading/predict/${encoded}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!r.ok) throw new Error('Stock not found');
      const d = await r.json();
      setSearchResult({
        name: d.symbol,
        symbol: d.symbol,
        current_price: d.current_price,
        '52_week_low': d.current_price * 0.8, // Mocked as backend needs full yfinance data
        '52_week_high': d.current_price * 1.2,
      });
      setTradeSymbol(d.symbol);
    } catch {
      setSearchResult({ error: `"${searchQuery.toUpperCase()}" not found. Try AAPL, TSLA, RELIANCE.NS` });
    } finally { setSearching(false); }
  };

  const handleTrade = async (action) => {
    if (!tradeSymbol || tradeQty < 1) {
      setTradeMsg({ type: 'error', text: 'Enter a valid symbol and quantity.' });
      return;
    }
    setTrading(true); setTradeMsg(null);
    try {
      const endpoint = action === 'BUY' ? '/api/trading/trade' : '/api/trading/trade';
      const res = await fetch(`${base}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ symbol: tradeSymbol, quantity: parseInt(tradeQty), side: action }),
      });
      const data = await res.json();
      if (!res.ok) {
        setTradeMsg({ type: 'error', text: data.detail || `${action} failed` });
      } else {
        setTradeMsg({ type: 'success', text: data.message || `${action} order placed!` });
        // Refresh wallet and transactions
        await fetchData();
      }
    } catch (e) {
      setTradeMsg({ type: 'error', text: 'Network error. Is the backend running?' });
    } finally { setTrading(false); }
  };

  const upCount = stocks.filter(s => s.change >= 0).length;

  return (
    <AppShell>
      {/* Greeting */}
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>
          Good {new Date().getHours() < 12 ? 'Morning' : new Date().getHours() < 17 ? 'Afternoon' : 'Evening'}, {user?.username} 👋
        </h1>
        <div className="text-muted text-xs" style={{ marginTop: 4 }}>
          {new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
        </div>
      </div>

      {/* Stat Cards */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Available Funds</div>
          <div className="stat-value text-green">₹{(wallet?.balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
          <div className="stat-sub text-muted">Paper trading balance</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Market Status</div>
          <div className="stat-value" style={{ fontSize: 15, color: marketStatus.color, display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}>
            {marketStatus.open ? (
              <>
                <span className="dot-live" style={{ width: 8, height: 8 }}></span>
                Open
              </>
            ) : (
              <>
                <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--red)', display: 'inline-block' }}></span>
                {marketStatus.text}
              </>
            )}
          </div>
          <div className="stat-sub text-muted">{marketStatus.detail} · {marketStatus.timeText}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Advancing / Declining</div>
          <div className="stat-value">
            <span className="text-green">{upCount}</span>
            <span className="text-muted" style={{ fontSize: 14, margin: '0 4px' }}>/</span>
            <span className="text-red">{stocks.length - upCount}</span>
          </div>
          <div className="stat-sub text-muted">In your watchlist</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Orders Placed</div>
          <div className="stat-value">{transactions.length}</div>
          <div className="stat-sub text-muted">Total trade history</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 16 }}>
        {/* Left — Watchlist + Search */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Stock Search */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Stock Search</span>
              <span className="text-xs text-muted">Try AAPL · TCS.NS · RELIANCE.NS</span>
            </div>
            <div className="card-body">
              <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8 }}>
                <input
                  className="form-input"
                  value={searchQuery}
                  onChange={e => setSearchQuery(e.target.value)}
                  placeholder="Enter stock symbol (e.g. INFY.NS)"
                  style={{ flex: 1 }}
                />
                <button type="submit" className="btn btn-primary" disabled={searching}>
                  {searching ? '...' : 'Search'}
                </button>
              </form>
              {searchResult && (
                <div style={{ marginTop: 12, padding: '12px 14px', background: 'var(--bg-main)', borderRadius: 6, border: '1px solid var(--border)' }}>
                  {searchResult.error ? (
                    <div className="text-red">{searchResult.error}</div>
                  ) : (
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 15 }}>{searchResult.name}</div>
                        <div className="text-xs text-muted">{searchResult.symbol} · {searchResult.exchange} · {searchResult.sector || ''}</div>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 18, fontWeight: 700 }}>₹{searchResult.current_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                        <div className="text-xs text-muted">52W: ₹{searchResult['52_week_low']?.toFixed(0)} – ₹{searchResult['52_week_high']?.toFixed(0)}</div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Market Watchlist */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Market Watchlist</span>
              <span className="text-xs text-muted">{upCount}/{stocks.length} advancing</span>
            </div>
            {loading ? (
              <div style={{ padding: 40, display: 'flex', justifyContent: 'center' }}><div className="loading-spinner"></div></div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 110px 70px 80px', padding: '8px 16px', borderBottom: '1px solid var(--border)' }}>
                  {['COMPANY', 'LTP', 'CHG%', 'ACTION'].map((h, i) => (
                    <span key={h} style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.5px', textAlign: i === 0 ? 'left' : 'right' }}>{h}</span>
                  ))}
                </div>
                {stocks.map(s => {
                  const isUp = s.change >= 0;
                  return (
                    <div key={s.symbol} className="table-row" style={{ gridTemplateColumns: '1fr 110px 70px 80px' }}
                      onClick={() => setTradeSymbol(s.symbol)}>
                      <div>
                        <div className="stock-name">{s.name}</div>
                        <div className="stock-sym">{s.symbol.replace('.NS', '')} · NSE</div>
                      </div>
                      <div className="price-val">₹{s.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                      <div style={{ textAlign: 'right' }}>
                        <span className={`change-chip ${isUp ? 'chip-green' : 'chip-red'}`}>
                          {isUp ? '+' : ''}{s.change?.toFixed(2)}%
                        </span>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <button className="btn btn-buy btn-sm" onClick={e => { e.stopPropagation(); setTradeSymbol(s.symbol); setTradeMsg(null); }}>B</button>
                      </div>
                    </div>
                  );
                })}
              </>
            )}
          </div>
        </div>

        {/* Right — Trade Panel + Orders */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Quick Trade */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Place Order</span>
              <span className="tag tag-blue">Paper Trade</span>
            </div>
            <div className="card-body">
              <div className="form-group">
                <label className="form-label">Symbol</label>
                <input className="form-input" value={tradeSymbol} onChange={e => setTradeSymbol(e.target.value.toUpperCase())} placeholder="e.g. RELIANCE.NS" />
              </div>
              <div className="form-group">
                <label className="form-label">Quantity</label>
                <input className="form-input" type="number" min="1" value={tradeQty} onChange={e => setTradeQty(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Order Type</label>
                <select className="form-input" value={tradeType} onChange={e => setTradeType(e.target.value)}>
                  <option value="market">Market Order</option>
                  <option value="limit">Limit Order</option>
                </select>
              </div>

              {tradeMsg && (
                <div style={{
                  padding: '10px 12px', borderRadius: 4, fontSize: 12, marginBottom: 12,
                  background: tradeMsg.type === 'success' ? 'var(--green-dim)' : 'var(--red-dim)',
                  color: tradeMsg.type === 'success' ? 'var(--green)' : 'var(--red)',
                  border: `1px solid ${tradeMsg.type === 'success' ? 'rgba(0,179,134,0.3)' : 'rgba(224,80,80,0.3)'}`,
                }}>
                  {tradeMsg.text}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <button className="btn btn-buy btn-block" disabled={trading} onClick={() => handleTrade('BUY')}>
                  {trading ? '...' : '▲ BUY'}
                </button>
                <button className="btn btn-sell btn-block" disabled={trading} onClick={() => handleTrade('SELL')}>
                  {trading ? '...' : '▼ SELL'}
                </button>
              </div>

              <div style={{ marginTop: 12, padding: '8px', background: 'var(--bg-main)', borderRadius: 4, fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
                Balance: ₹{(wallet?.balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* Recent Orders */}
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header">
              <span className="card-title">Recent Orders</span>
              <span className="text-xs text-muted">{transactions.length} total</span>
            </div>
            {transactions.length === 0 ? (
              <div className="empty-state" style={{ padding: '28px 16px' }}>
                <div style={{ fontSize: 28, marginBottom: 8 }}>📋</div>
                <div>No orders yet. Place your first trade!</div>
              </div>
            ) : (
              transactions.slice(0, 6).map(tx => (
                <div key={tx.id} className="table-row" style={{ gridTemplateColumns: '1fr auto' }}>
                  <div>
                    <div className="stock-name">{tx.stock_symbol}</div>
                    <div className="text-xs text-muted">{tx.action} · {tx.quantity} qty @ ₹{tx.price?.toFixed(2)}</div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 600, color: tx.action === 'BUY' ? 'var(--green)' : 'var(--red)', fontSize: 13 }}>
                      {tx.action === 'BUY' ? '▲' : '▼'} ₹{(tx.price * tx.quantity).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                    <div className="text-xs text-muted">{new Date(tx.created_at).toLocaleDateString('en-IN')}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </AppShell>
  );
};

export default DashboardPage;
