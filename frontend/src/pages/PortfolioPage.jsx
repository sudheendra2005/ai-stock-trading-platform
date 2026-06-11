import React, { useState, useEffect } from 'react';
import AppShell from '../components/AppShell';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';

const PortfolioPage = () => {
  const { user } = useAuth();
  const [portfolio, setPortfolio] = useState({ portfolio: [], summary: {} });
  const [loading, setLoading] = useState(true);
  const [selling, setSelling] = useState(null);
  const [sellQty, setSellQty] = useState({});
  const [msg, setMsg] = useState(null);

  const token = localStorage.getItem('token');
  const base = API_BASE;

  const fetchPortfolio = async () => {
    try {
      const r = await fetch(`${base}/api/trading/portfolio`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      // API returns { portfolio: [...], summary: {...} }
      setPortfolio(d);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchPortfolio(); }, []);

  const handleSell = async (symbol, maxQty) => {
    const qty = parseInt(sellQty[symbol] || 1);
    if (qty < 1 || qty > maxQty) {
      setMsg({ type: 'error', text: `You own ${maxQty} shares of ${symbol}` });
      return;
    }
    setSelling(symbol);
    try {
      const res = await fetch(`${base}/api/trading/trade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ symbol: symbol, quantity: qty, side: 'SELL' }),
      });
      const data = await res.json();
      if (!res.ok) {
        setMsg({ type: 'error', text: data.detail || 'Sell failed' });
      } else {
        setMsg({ type: 'success', text: data.message || `Sold ${qty} shares of ${symbol}` });
        await fetchPortfolio();
      }
    } catch {
      setMsg({ type: 'error', text: 'Network error' });
    } finally {
      setSelling(null);
      setTimeout(() => setMsg(null), 4000);
    }
  };

  const { portfolio: items, summary } = portfolio;
  const totalPL = summary?.total_profit_loss || 0;
  const totalPLPct = summary?.total_profit_loss_percent || 0;

  return (
    <AppShell>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>Holdings</h1>
        <div className="text-muted text-xs" style={{ marginTop: 4 }}>Your current stock positions with live P&amp;L</div>
      </div>

      {/* Summary */}
      <div className="stat-grid">
        <div className="stat-card">
          <div className="stat-label">Invested Value</div>
          <div className="stat-value">₹{(summary?.total_investment || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
          <div className="stat-sub text-muted">Cost basis</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Current Value</div>
          <div className="stat-value">₹{(summary?.total_current_value || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
          <div className="stat-sub text-muted">Mark to market</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total P&amp;L</div>
          <div className={`stat-value ${totalPL >= 0 ? 'text-green' : 'text-red'}`}>
            {totalPL >= 0 ? '+' : ''}₹{totalPL.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
          </div>
          <div className={`stat-sub ${totalPL >= 0 ? 'text-green' : 'text-red'}`}>
            {totalPLPct >= 0 ? '+' : ''}{totalPLPct.toFixed(2)}% overall
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Positions</div>
          <div className="stat-value">{items?.length || 0}</div>
          <div className="stat-sub text-muted">Stocks held</div>
        </div>
      </div>

      {/* Message */}
      {msg && (
        <div style={{
          padding: '10px 14px', marginBottom: 14, borderRadius: 4, fontSize: 13,
          background: msg.type === 'success' ? 'var(--green-dim)' : 'var(--red-dim)',
          color: msg.type === 'success' ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${msg.type === 'success' ? 'rgba(0,179,134,0.3)' : 'rgba(224,80,80,0.3)'}`,
        }}>
          {msg.text}
        </div>
      )}

      {/* Holdings Table */}
      <div className="card">
        <div className="card-header">
          <span className="card-title">Open Positions</span>
          <span className="text-xs text-muted">{items?.length || 0} stocks</span>
        </div>

        {loading ? (
          <div style={{ padding: 40, display: 'flex', justifyContent: 'center' }}><div className="loading-spinner"></div></div>
        ) : !items || items.length === 0 ? (
          <div className="empty-state" style={{ padding: '48px 16px' }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>📊</div>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No holdings yet</div>
            <div className="text-xs text-muted">Go to Dashboard and place a BUY order to start building your portfolio</div>
          </div>
        ) : (
          <>
            {/* Column headers */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 80px 90px 90px 90px 90px 100px', padding: '8px 16px', borderBottom: '1px solid var(--border)' }}>
              {['STOCK', 'QTY', 'AVG COST', 'CUR PRICE', 'INVESTED', 'CUR VALUE', 'P&L'].map((h, i) => (
                <span key={h} style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.5px', textAlign: i === 0 ? 'left' : 'right' }}>{h}</span>
              ))}
            </div>

            {items.map(item => {
              const pl = item.profit_loss;
              const plPct = item.profit_loss_percent;
              const isProfit = pl >= 0;
              return (
                <div key={item.id}>
                  <div className="table-row" style={{ gridTemplateColumns: '1.5fr 80px 90px 90px 90px 90px 100px' }}>
                    <div>
                      <div className="stock-name">{item.stock_symbol}</div>
                    </div>
                    <div style={{ textAlign: 'right', fontWeight: 600 }}>{item.quantity}</div>
                    <div style={{ textAlign: 'right', fontWeight: 600 }}>₹{item.buy_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ textAlign: 'right', fontWeight: 600 }}>₹{item.current_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ textAlign: 'right' }}>₹{item.investment?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ textAlign: 'right' }}>₹{item.current_value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 700, color: isProfit ? 'var(--green)' : 'var(--red)', fontSize: 13 }}>
                        {isProfit ? '+' : ''}₹{pl?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                      <div style={{ fontSize: 10, color: isProfit ? 'var(--green)' : 'var(--red)' }}>
                        {isProfit ? '+' : ''}{plPct?.toFixed(2)}%
                      </div>
                    </div>
                  </div>
                  {/* Sell row */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 16px 10px', borderBottom: '1px solid var(--border)', background: 'var(--bg-main)' }}>
                    <span className="text-xs text-muted">Sell:</span>
                    <input
                      type="number" min="1" max={item.quantity} defaultValue={1}
                      className="form-input" style={{ width: 60, padding: '4px 8px', fontSize: 12 }}
                      onChange={e => setSellQty(prev => ({ ...prev, [item.stock_symbol]: e.target.value }))}
                    />
                    <span className="text-xs text-muted">of {item.quantity} shares</span>
                    <button
                      className="btn btn-sell btn-sm"
                      disabled={selling === item.stock_symbol}
                      onClick={() => handleSell(item.stock_symbol, item.quantity)}
                    >
                      {selling === item.stock_symbol ? 'Selling...' : 'SELL'}
                    </button>
                  </div>
                </div>
              );
            })}
          </>
        )}
      </div>
    </AppShell>
  );
};

export default PortfolioPage;
