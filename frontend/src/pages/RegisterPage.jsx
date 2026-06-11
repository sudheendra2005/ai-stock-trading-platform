import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const RegisterPage = () => {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '', confirmPassword: '' });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');

  const set = (e) => setForm(p => ({ ...p, [e.target.name]: e.target.value }));

  const validate = () => {
    const errs = {};
    if (!form.username.trim()) errs.username = 'Username required';
    if (!form.email.trim()) errs.email = 'Email required';
    else if (!/\S+@\S+\.\S+/.test(form.email)) errs.email = 'Enter a valid email address';
    if (!form.password) errs.password = 'Password required';
    else if (form.password.length < 6) errs.password = 'Minimum 6 characters';
    if (form.password !== form.confirmPassword) errs.confirmPassword = 'Passwords do not match';
    return errs;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = validate();
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setLoading(true); setErrors({});
    const result = await register(form.username, form.email, form.password);
    setLoading(false);
    if (result.success) {
      setSuccess('Account created! Redirecting to login...');
      setTimeout(() => navigate('/login'), 2000);
    } else {
      const msg = result.message || 'Registration failed';
      if (msg.toLowerCase().includes('email')) setErrors({ email: msg });
      else if (msg.toLowerCase().includes('username')) setErrors({ username: msg });
      else setErrors({ form: msg });
    }
  };

  return (
    <div className="auth-page">
      {/* Brand panel */}
      <div className="auth-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 48 }}>
          <div style={{ width: 32, height: 32, background: '#00b386', borderRadius: 6, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 16, color: '#000' }}>N</div>
          <span style={{ fontWeight: 700, fontSize: 18 }}>NexusAI</span>
        </div>
        <h2 style={{ fontSize: 28, fontWeight: 700, lineHeight: 1.3, marginBottom: 16 }}>
          India's smartest <span style={{ color: '#00b386' }}>AI trading</span> platform
        </h2>
        <p style={{ color: '#6a6a6a', fontSize: 14, lineHeight: 1.7, marginBottom: 40 }}>
          Practice trading on real NSE/BSE data with ₹1,00,000 virtual money. Get AI buy/sell signals and learn to invest smartly.
        </p>
        {[
          ['✓', 'Free ₹1,00,000 virtual money'],
          ['✓', 'Live NSE/BSE stock prices'],
          ['✓', 'AI-powered buy/sell signals'],
          ['✓', 'No real money involved'],
        ].map(([icon, text]) => (
          <div key={text} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, color: '#a0a0a0', fontSize: 13 }}>
            <span style={{ color: '#00b386', fontWeight: 700 }}>{icon}</span>{text}
          </div>
        ))}
      </div>

      {/* Form panel */}
      <div className="auth-form-wrap">
        <div className="auth-form-card">
          <div className="auth-title">Create account</div>
          <div className="auth-subtitle">Already have an account? <Link to="/login" className="auth-link">Sign in</Link></div>

          {success && (
            <div style={{ background: 'var(--green-dim)', border: '1px solid rgba(0,179,134,0.3)', color: 'var(--green)', padding: '10px 14px', borderRadius: 4, fontSize: 13, marginBottom: 16 }}>
              {success}
            </div>
          )}
          {errors.form && (
            <div style={{ background: 'var(--red-dim)', border: '1px solid rgba(224,80,80,0.3)', color: 'var(--red)', padding: '10px 14px', borderRadius: 4, fontSize: 13, marginBottom: 16 }}>
              {errors.form}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label className="form-label">Full Name / Username</label>
              <input className="form-input" name="username" value={form.username} onChange={set} placeholder="e.g. Suresh Kumar" />
              {errors.username && <div className="form-error">{errors.username}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input className="form-input" name="email" type="email" value={form.email} onChange={set} placeholder="name@email.com" />
              {errors.email && <div className="form-error">{errors.email}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Password</label>
              <input className="form-input" name="password" type="password" value={form.password} onChange={set} placeholder="Min. 6 characters" />
              {errors.password && <div className="form-error">{errors.password}</div>}
            </div>
            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input className="form-input" name="confirmPassword" type="password" value={form.confirmPassword} onChange={set} placeholder="Re-enter password" />
              {errors.confirmPassword && <div className="form-error">{errors.confirmPassword}</div>}
            </div>
            <button type="submit" disabled={loading} className="btn btn-primary btn-block" style={{ marginTop: 8, padding: '11px 0', fontSize: 14 }}>
              {loading ? 'Creating account...' : 'Create Account'}
            </button>
          </form>
          <p style={{ marginTop: 16, fontSize: 11, color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.6 }}>
            By creating an account, you agree this is a paper trading demo only. No real financial transactions occur.
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;
