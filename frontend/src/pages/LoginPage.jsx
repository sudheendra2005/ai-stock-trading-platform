import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const LoginPage = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const set = (e) => setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = {};
    if (!form.email.trim()) errs.email = 'Email required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email';
    if (!form.password) errs.password = 'Password required';
    if (Object.keys(errs).length) { setErrors(errs); return; }

    setLoading(true); setErrors({});
    const result = await login(form.email, form.password);
    setLoading(false);
    if (result.success) {
      navigate('/dashboard', { replace: true });
    } else {
      setErrors({ form: result.message || 'Invalid email or password' });
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 48 }}>
          <div style={{ width: 32, height: 32, background: '#00b386', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, color: '#000' }}>N</div>
          <span style={{ fontWeight: 700, fontSize: 18 }}>NexusAI</span>
        </div>
        <h2 style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.3, marginBottom: 16 }}>
          Welcome back to your <span style={{ color: '#00b386' }}>trading terminal</span>
        </h2>
        <p style={{ color: '#6a6a6a', fontSize: 14, lineHeight: 1.7 }}>
          Log in to access your portfolio, AI predictions, and live NSE/BSE market data.
        </p>
      </div>

      <div className="auth-form-wrap">
        <div className="auth-form-card">
          <div className="auth-title">Sign in</div>
          <div className="auth-subtitle">New to NexusAI? <Link to="/register" className="auth-link">Create free account</Link></div>

          {errors.form && (
            <div style={{ background: 'var(--red-dim)', border: '1px solid rgba(224,80,80,0.3)', color: 'var(--red)', padding: '10px 14px', borderRadius: 4, fontSize: 13, marginBottom: 16 }}>
              {errors.form}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input className="form-input" name="email" type="email" value={form.email} onChange={set} placeholder="name@email.com" autoFocus />
              {errors.email && <div className="form-error">{errors.email}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" name="password" type="password" value={form.password} onChange={set} placeholder="Your password" />
              {errors.password && <div className="form-error">{errors.password}</div>}
            </div>
            <button type="submit" disabled={loading} className="btn btn-primary btn-block" style={{ marginTop: 8, padding: '11px 0', fontSize: 14 }}>
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          <p style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)', textAlign: 'center' }}>
            This is a paper trading platform. No real funds involved.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
