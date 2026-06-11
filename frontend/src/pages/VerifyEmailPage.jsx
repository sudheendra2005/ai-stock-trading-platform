import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';

const VerifyEmailPage = () => {
  const { verifyEmail } = useAuth();
  const navigate = useNavigate();
  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    const res = await verifyEmail(token);
    setLoading(false);
    if (res.success) {
      setMessage('Node connection verified successfully. Redirecting...');
      setTimeout(() => navigate('/login'), 2000);
    } else {
      setMessage(res.message);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-8">
      <div className="glass-panel p-8 max-w-md w-full text-center">
        <h2 className="text-2xl font-bold mb-4">Verify Node Link</h2>
        <p className="text-gray-400 mb-6">Enter the verification hash sent to your comms vector.</p>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <input 
            type="text" 
            value={token} 
            onChange={e => setToken(e.target.value)} 
            placeholder="Verification Hash"
            className="w-full glass-input p-3 rounded-xl text-center"
          />
          <button type="submit" disabled={loading} className="w-full btn-neon py-3 rounded-xl font-bold">
            {loading ? 'Verifying...' : 'Authenticate Link'}
          </button>
        </form>
        {message && <p className="mt-4 text-neon">{message}</p>}
        <Link to="/login" className="block mt-6 text-gray-500 hover:text-white">Cancel</Link>
      </div>
    </div>
  );
};

export default VerifyEmailPage;
