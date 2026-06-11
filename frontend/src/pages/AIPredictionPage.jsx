import React, { useState, useEffect } from 'react';
import AppShell from '../components/AppShell';
import { useAuth } from '../context/AuthContext';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { API_BASE } from '../config/api';

const STOCKS = [
  { sym: 'RELIANCE.NS', name: 'Reliance Industries', sector: 'Energy' },
  { sym: 'TCS.NS', name: 'Tata Consultancy Services', sector: 'IT' },
  { sym: 'HDFCBANK.NS', name: 'HDFC Bank', sector: 'Banking' },
  { sym: 'INFY.NS', name: 'Infosys', sector: 'IT' },
  { sym: 'ICICIBANK.NS', name: 'ICICI Bank', sector: 'Banking' },
  { sym: 'WIPRO.NS', name: 'Wipro Ltd', sector: 'IT' },
  { sym: 'AAPL', name: 'Apple Inc.', sector: 'Tech' },
  { sym: 'MSFT', name: 'Microsoft Corp', sector: 'Tech' },
  { sym: 'GOOGL', name: 'Alphabet Inc.', sector: 'Tech' },
];

const SignalBadge = ({ signal }) => {
  const s = (signal || 'HOLD').toUpperCase();
  const cls = s === 'BUY' ? 'signal-buy' : s === 'SELL' ? 'signal-sell' : 'signal-hold';
  const icon = s === 'BUY' ? '▲' : s === 'SELL' ? '▼' : '—';
  return <span className={`signal-badge ${cls}`}>{icon} {s}</span>;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 4, padding: '8px 12px', fontSize: 12 }}>
        <div className="text-muted" style={{ marginBottom: 2 }}>{label}</div>
        <div style={{ fontWeight: 700, color: 'var(--blue)' }}>₹{payload[0].value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
      </div>
    );
  }
  return null;
};

const AIPredictionPage = () => {
  const [selected, setSelected] = useState(null);
  const [predictions, setPredictions] = useState({});
  const [rlPredictions, setRlPredictions] = useState({});
  const [stockDetails, setStockDetails] = useState({});
  const [loading, setLoading] = useState({});
  const [rlTraining, setRlTraining] = useState({});
  const [leaderboard, setLeaderboard] = useState([]);
  const [leaderboardLoading, setLeaderboardLoading] = useState(false);
  const [batchTraining, setBatchTraining] = useState(false);
  const [detailLoading, setDetailLoading] = useState({});
  const base = API_BASE;

  const fetchLeaderboard = async () => {
    setLeaderboardLoading(true);
    try {
      const response = await fetch(`${base}/api/rl/leaderboard`);
      const data = await response.json();
      setLeaderboard(response.ok ? data.leaderboard || [] : []);
    } catch {
      setLeaderboard([]);
    } finally {
      setLeaderboardLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchPrediction = async (sym) => {
    if (predictions[sym] && rlPredictions[sym]) { setSelected(sym); return; }
    setSelected(sym);
    setLoading(prev => ({ ...prev, [sym]: true }));
    setDetailLoading(prev => ({ ...prev, [sym]: true }));

    try {
      const [predResponse, detailResponse, rlResponse] = await Promise.all([
        fetch(`${base}/api/stocks/predict/${encodeURIComponent(sym)}`),
        fetch(`${base}/api/stocks/${encodeURIComponent(sym)}`),
        fetch(`${base}/api/rl/recommend/${encodeURIComponent(sym)}`),
      ]);
      const [predRes, detailRes, rlRes] = await Promise.all([
        predResponse.json(),
        detailResponse.json(),
        rlResponse.json(),
      ]);
      if (!predResponse.ok) {
        throw new Error(predRes.detail || 'Failed to fetch prediction');
      }
      if (!detailResponse.ok) {
        throw new Error(detailRes.detail || 'Failed to fetch stock details');
      }
      setPredictions(prev => ({ ...prev, [sym]: predRes }));
      setStockDetails(prev => ({ ...prev, [sym]: detailRes }));
      setRlPredictions(prev => ({
        ...prev,
        [sym]: rlResponse.ok ? rlRes : { error: rlRes.detail || 'RL agent unavailable' }
      }));
    } catch (error) {
      setPredictions(prev => ({ ...prev, [sym]: { error: error.message || 'Failed to fetch prediction' } }));
    } finally {
      setLoading(prev => ({ ...prev, [sym]: false }));
      setDetailLoading(prev => ({ ...prev, [sym]: false }));
    }
  };

  const pred = selected && predictions[selected];
  const rlPred = selected && rlPredictions[selected];
  const detail = selected && stockDetails[selected];
  const stockInfo = selected && STOCKS.find(s => s.sym === selected);

  // Build chart data from historical
  const chartData = detail?.historical_data?.map(d => ({
    date: d.date?.slice(5), // MM-DD
    close: d.close,
  })) || [];

  const retrainRlAgent = async () => {
    if (!selected) return;
    setRlTraining(prev => ({ ...prev, [selected]: true }));
    setRlPredictions(prev => ({ ...prev, [selected]: null }));
    try {
      const trainResponse = await fetch(`${base}/api/rl/train/${encodeURIComponent(selected)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ episodes: 90, force: true }),
      });
      const trainResult = await trainResponse.json();
      if (!trainResponse.ok) {
        throw new Error(trainResult.detail || 'RL training failed');
      }
      const recommendResponse = await fetch(`${base}/api/rl/recommend/${encodeURIComponent(selected)}`);
      const recommendResult = await recommendResponse.json();
      if (!recommendResponse.ok) {
        throw new Error(recommendResult.detail || 'RL recommendation failed');
      }
      setRlPredictions(prev => ({ ...prev, [selected]: recommendResult }));
      fetchLeaderboard();
    } catch (error) {
      setRlPredictions(prev => ({ ...prev, [selected]: { error: error.message || 'RL training failed' } }));
    } finally {
      setRlTraining(prev => ({ ...prev, [selected]: false }));
    }
  };

  const trainWatchlist = async () => {
    setBatchTraining(true);
    try {
      const response = await fetch(`${base}/api/rl/train-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbols: STOCKS.map(s => s.sym),
          episodes: 70,
          force: true,
        }),
      });
      if (response.ok) {
        await fetchLeaderboard();
        if (selected) {
          const recommendResponse = await fetch(`${base}/api/rl/recommend/${encodeURIComponent(selected)}`);
          const recommendResult = await recommendResponse.json();
          if (recommendResponse.ok) {
            setRlPredictions(prev => ({ ...prev, [selected]: recommendResult }));
          }
        }
      }
    } finally {
      setBatchTraining(false);
    }
  };

  return (
    <AppShell>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 18, fontWeight: 700 }}>AI Predictions</h1>
        <div className="text-muted text-xs" style={{ marginTop: 4 }}>Neural engine · MA · RSI · MACD · Short & Long term signals</div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 16, alignItems: 'start' }}>
        {/* Stock list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <div className="card">
          <div className="card-header"><span className="card-title">Select Stock</span></div>
          {STOCKS.map(s => (
            <div
              key={s.sym}
              onClick={() => fetchPrediction(s.sym)}
              className="table-row"
              style={{
                gridTemplateColumns: '1fr auto',
                cursor: 'pointer',
                background: selected === s.sym ? 'var(--bg-hover)' : undefined,
                borderLeft: `3px solid ${selected === s.sym ? 'var(--blue)' : 'transparent'}`,
              }}
            >
              <div>
                <div className="stock-name">{s.name}</div>
                <div className="text-xs text-muted">{s.sym.replace('.NS', '')} · {s.sector}</div>
              </div>
              <div>
                {loading[s.sym]
                  ? <div className="loading-spinner" style={{ width: 14, height: 14, borderWidth: 2 }}></div>
                  : predictions[s.sym] && !predictions[s.sym].error
                    ? <SignalBadge signal={predictions[s.sym].recommendation} />
                    : null}
              </div>
            </div>
          ))}
        </div>

          <div className="card">
            <div className="card-header">
              <span className="card-title">RL Leaderboard</span>
              <button type="button" className="btn btn-ghost btn-sm" onClick={trainWatchlist} disabled={batchTraining}>
                {batchTraining ? 'Training...' : 'Train All'}
              </button>
            </div>
            {leaderboardLoading ? (
              <div style={{ padding: 24, display: 'flex', justifyContent: 'center' }}><div className="loading-spinner"></div></div>
            ) : leaderboard.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 12px' }}>
                <div>No RL policies yet</div>
              </div>
            ) : (
              leaderboard.slice(0, 6).map(row => (
                <div
                  key={row.symbol}
                  className="table-row"
                  onClick={() => fetchPrediction(row.symbol)}
                  style={{ gridTemplateColumns: '1fr auto', cursor: 'pointer' }}
                >
                  <div>
                    <div className="stock-name">{row.symbol.replace('.NS', '')}</div>
                    <div className="text-xs text-muted">
                      {row.grade || 'C'} · {((row.excess_return || 0) * 100).toFixed(1)}% excess · DD {(Math.abs(row.max_drawdown || 0) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <SignalBadge signal={row.action} />
                </div>
              ))
            )}
          </div>
        </div>

        {/* Detail panel */}
        <div>
          {!selected ? (
            <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
              <div className="empty-state">
                <div style={{ fontSize: 36, marginBottom: 12 }}>◈</div>
                <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>Select a stock to analyse</div>
                <div className="text-xs text-muted">AI will generate BUY / SELL / HOLD signals with indicators</div>
              </div>
            </div>
          ) : loading[selected] ? (
            <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 60 }}>
              <div style={{ textAlign: 'center' }}>
                <div className="loading-spinner" style={{ margin: '0 auto 12px' }}></div>
                <div className="text-xs text-muted">Fetching live data & running neural engine...</div>
              </div>
            </div>
          ) : pred?.error ? (
            <div className="card" style={{ padding: 24 }}>
              <div className="text-red">Error: {pred.error}</div>
            </div>
          ) : pred ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Header */}
              <div className="card">
                <div className="card-body">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 20 }}>
                    <div>
                      <div style={{ fontSize: 20, fontWeight: 700 }}>{stockInfo?.name}</div>
                      <div className="text-xs text-muted" style={{ marginTop: 4 }}>
                        {selected.replace('.NS', '')} · {detail?.exchange || 'NSE'} · {detail?.sector || stockInfo?.sector}
                      </div>
                    </div>
                    <SignalBadge signal={pred.recommendation} />
                  </div>

                  {/* Key metrics */}
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
                    {[
                      { label: 'Current Price', value: `₹${pred.current_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`, color: 'var(--text-primary)' },
                      { label: 'Confidence', value: pred.confidence || 'N/A', color: 'var(--blue)' },
                      { label: 'Short Term', value: pred.short_term || 'N/A', color: pred.short_term === 'UPTREND' ? 'var(--green)' : pred.short_term === 'DOWNTREND' ? 'var(--red)' : 'var(--yellow)' },
                      { label: 'Long Term', value: pred.long_term || 'N/A', color: pred.long_term === 'BULLISH' ? 'var(--green)' : pred.long_term === 'BEARISH' ? 'var(--red)' : 'var(--yellow)' },
                      { label: 'Risk Level', value: pred.risk || 'N/A', color: pred.risk === 'HIGH' ? 'var(--red)' : pred.risk === 'LOW' ? 'var(--green)' : 'var(--yellow)' },
                    ].map(m => (
                      <div key={m.label} style={{ background: 'var(--bg-main)', padding: '12px', borderRadius: 6 }}>
                        <div className="text-xs text-muted" style={{ marginBottom: 6 }}>{m.label}</div>
                        <div style={{ fontWeight: 700, fontSize: 15, color: m.color }}>{m.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Price Chart */}
              {chartData.length > 0 && (
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">30-Day Price Chart</span>
                    <span className="text-xs text-muted">Close price · {chartData.length} days</span>
                  </div>
                  <div style={{ padding: '16px 8px 8px' }}>
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis dataKey="date" tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} tickLine={false} axisLine={false} interval={4} />
                        <YAxis tick={{ fill: 'var(--text-secondary)', fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={v => `₹${v.toLocaleString('en-IN')}`} width={80} />
                        <Tooltip content={<CustomTooltip />} />
                        <Line type="monotone" dataKey="close" stroke="var(--blue)" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Two-column: Technical Indicators + Stock Details */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <div className="card">
                  <div className="card-header">
                    <span className="card-title">RL Agent</span>
                    <button
                      type="button"
                      className="btn btn-ghost btn-sm"
                      onClick={retrainRlAgent}
                      disabled={rlTraining[selected]}
                    >
                      {rlTraining[selected] ? 'Training...' : 'Retrain'}
                    </button>
                  </div>
                  <div className="card-body">
                    {rlPred?.error ? (
                      <div className="text-red" style={{ fontSize: 12 }}>{rlPred.error}</div>
                    ) : rlPred ? (
                      <>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
                          <span className="text-muted" style={{ fontSize: 12 }}>Policy Action</span>
                          <SignalBadge signal={rlPred.action} />
                        </div>
                        {[
                          { label: 'Confidence', value: `${Math.round((rlPred.confidence || 0) * 100)}%` },
                          { label: 'Expected Reward', value: rlPred.expected_reward?.toFixed ? rlPred.expected_reward.toFixed(5) : rlPred.expected_reward },
                          { label: 'Backtest Return', value: `${((rlPred.backtest?.strategy_return || 0) * 100).toFixed(2)}%` },
                          { label: 'Holdout Return', value: `${((rlPred.holdout_backtest?.strategy_return || 0) * 100).toFixed(2)}%` },
                          { label: 'Max Drawdown', value: `${(Math.abs(rlPred.holdout_backtest?.max_drawdown || rlPred.backtest?.max_drawdown || 0) * 100).toFixed(2)}%` },
                          { label: 'Sharpe', value: (rlPred.holdout_backtest?.sharpe ?? rlPred.backtest?.sharpe ?? 0).toFixed(2) },
                          { label: 'Grade', value: rlPred.grade || 'N/A' },
                          { label: 'Buy & Hold', value: `${((rlPred.backtest?.buy_hold_return || 0) * 100).toFixed(2)}%` },
                          { label: 'Sim Trades', value: rlPred.backtest?.trades ?? 'N/A' },
                          { label: 'Risk', value: rlPred.risk || 'N/A' },
                          { label: 'Policy Saved', value: rlPred.created_at ? new Date(rlPred.created_at).toLocaleDateString('en-IN') : 'N/A' },
                        ].map(row => (
                          <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                            <span className="text-muted" style={{ fontSize: 12 }}>{row.label}</span>
                            <span style={{ fontWeight: 600, fontSize: 13 }}>{row.value}</span>
                          </div>
                        ))}
                      </>
                    ) : (
                      <div className="text-muted" style={{ fontSize: 12 }}>Training agent...</div>
                    )}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><span className="card-title">Technical Indicators</span></div>
                  <div className="card-body">
                    {[
                      { label: 'RSI (14)', value: pred.indicators?.rsi?.toFixed(2) || '—', note: pred.indicators?.rsi < 30 ? 'Oversold' : pred.indicators?.rsi > 70 ? 'Overbought' : 'Neutral', noteColor: pred.indicators?.rsi < 30 ? 'var(--green)' : pred.indicators?.rsi > 70 ? 'var(--red)' : 'var(--text-secondary)' },
                      { label: 'MACD', value: pred.indicators?.macd?.toFixed(4) || '—', note: pred.indicators?.macd > 0 ? 'Bullish' : 'Bearish', noteColor: pred.indicators?.macd > 0 ? 'var(--green)' : 'var(--red)' },
                      { label: 'Volatility (Ann.)', value: pred.indicators?.volatility ? `${(pred.indicators.volatility * 100).toFixed(1)}%` : '—', note: pred.risk, noteColor: pred.risk === 'HIGH' ? 'var(--red)' : pred.risk === 'LOW' ? 'var(--green)' : 'var(--yellow)' },
                    ].map(row => (
                      <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                        <span className="text-muted" style={{ fontSize: 12 }}>{row.label}</span>
                        <div style={{ textAlign: 'right' }}>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>{row.value}</div>
                          <div style={{ fontSize: 10, color: row.noteColor }}>{row.note}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="card">
                  <div className="card-header"><span className="card-title">Stock Details</span></div>
                  <div className="card-body">
                    {[
                      { label: '52W High', value: detail?.['52_week_high'] ? `₹${detail['52_week_high']?.toFixed(2)}` : '—' },
                      { label: '52W Low', value: detail?.['52_week_low'] ? `₹${detail['52_week_low']?.toFixed(2)}` : '—' },
                      { label: 'P/E Ratio', value: detail?.pe_ratio?.toFixed(2) || '—' },
                      { label: 'Market Cap', value: detail?.market_cap ? `₹${(detail.market_cap / 1e9).toFixed(1)}B` : '—' },
                    ].map(row => (
                      <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
                        <span className="text-muted" style={{ fontSize: 12 }}>{row.label}</span>
                        <span style={{ fontWeight: 600, fontSize: 13 }}>{row.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div style={{ padding: '10px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11, color: 'var(--text-muted)' }}>
                ⚠ AI predictions are based on technical analysis only. Not financial advice. Past performance is not indicative of future results.
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </AppShell>
  );
};

export default AIPredictionPage;
