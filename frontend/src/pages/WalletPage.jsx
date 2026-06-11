import React, { useState, useEffect } from 'react';
import AppShell from '../components/AppShell';
import { useAuth } from '../context/AuthContext';
import { API_BASE } from '../config/api';

const WalletPage = () => {
  const { user } = useAuth();
  const [wallet, setWallet] = useState({ balance: 100000 });
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [amount, setAmount] = useState('');
  const [msg, setMsg] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    const base = API_BASE;
    Promise.all([
      fetch(`${base}/api/trading/wallet`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      fetch(`${base}/api/trading/transactions`, { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
    ]).then(([w, t]) => {
      setWallet(w);
      setTransactions(Array.isArray(t) ? t : []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleAdd = (e) => {
    e.preventDefault();
    const v = parseFloat(amount);
    if (!v || v <= 0) { setMsg('Enter a valid amount'); return; }
    setWallet(prev => ({ ...prev, balance: (prev.balance || 0) + v }));
    setTransactions(prev => [{
      id: Date.now(), stock_symbol: 'CASH', action: 'CREDIT',
      quantity: 1, price: v, created_at: new Date().toISOString()
    }, ...prev]);
    setAmount(''); setMsg(`₹${v.toLocaleString('en-IN')} added successfully!`);
    setTimeout(() => setMsg(''), 3000);
  };

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-20">
        <div>
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>Funds</h1>
          <div className="text-muted text-xs mt-8">Manage your paper trading balance</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 16 }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {/* Balance Card */}
          <div className="card">
            <div className="card-body">
              <div className="text-xs text-muted mb-8">Available Balance</div>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--green)', marginBottom: 4 }}>
                ₹{(wallet?.balance || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </div>
              <div className="text-xs text-muted">Paper money · Not real funds</div>
            </div>
          </div>

          {/* Add Funds */}
          <div className="card">
            <div className="card-header"><span className="card-title">Add Funds</span></div>
            <div className="card-body">
              <form onSubmit={handleAdd}>
                {[10000, 25000, 50000].map(v => (
                  <button key={v} type="button" onClick={() => setAmount(String(v))}
                    className="btn btn-ghost btn-sm"
                    style={{ marginRight: 6, marginBottom: 10 }}>
                    +₹{v.toLocaleString('en-IN')}
                  </button>
                ))}
                <div className="form-group mt-8">
                  <label className="form-label">Custom Amount (₹)</label>
                  <input className="form-input" type="number" value={amount} onChange={e => setAmount(e.target.value)} placeholder="Enter amount" />
                </div>
                {msg && <div style={{ padding: '8px 10px', background: 'var(--green-dim)', color: 'var(--green)', borderRadius: 4, fontSize: 12, marginBottom: 10 }}>{msg}</div>}
                <button type="submit" className="btn btn-primary btn-block">Add Funds</button>
              </form>
            </div>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">Transaction History</span>
            <span className="text-xs text-muted">{transactions.length} records</span>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 80px 100px 100px', padding: '8px 16px', borderBottom: '1px solid var(--border)' }}>
            {['STOCK', 'TYPE', 'AMOUNT', 'DATE'].map(h => (
              <span key={h} style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, letterSpacing: '0.5px', textAlign: h === 'STOCK' ? 'left' : 'right' }}>{h}</span>
            ))}
          </div>
          {loading ? (
            <div style={{ padding: 40, display: 'flex', justifyContent: 'center' }}><div className="loading-spinner"></div></div>
          ) : transactions.length === 0 ? (
            <div className="empty-state"><div style={{ fontSize: 30, marginBottom: 10 }}>📋</div><div>No transactions yet</div></div>
          ) : (
            transactions.map(tx => (
              <div key={tx.id} className="table-row" style={{ gridTemplateColumns: '1fr 80px 100px 100px' }}>
                <div>
                  <div className="stock-name">{tx.stock_symbol}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`tag ${tx.action === 'BUY' ? 'tag-green' : tx.action === 'SELL' ? 'tag-red' : 'tag-blue'}`}>{tx.action}</span>
                </div>
                <div style={{ textAlign: 'right', fontWeight: 600 }}>
                  ₹{(tx.price * tx.quantity).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ textAlign: 'right', color: 'var(--text-secondary)', fontSize: 11 }}>
                  {new Date(tx.created_at).toLocaleDateString('en-IN')}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
};

export default WalletPage;
