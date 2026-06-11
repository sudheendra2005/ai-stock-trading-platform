import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';
import { API_BASE } from '../config/api';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [emailSent, setEmailSent] = useState(false);
  const [resetEmailSent, setResetEmailSent] = useState(false);

  useEffect(() => {
    const init = async () => {
      const storedToken = localStorage.getItem('token');
      if (storedToken) {
        setToken(storedToken);
      try {
        const response = await axios.get(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${storedToken}` }
        });
        setUser(response.data);
      } catch (error) {
        localStorage.removeItem('token');
        setToken('');
      }

      }
      setLoading(false);
    };
    
    init();
  }, []);

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/login`, {
        email,
        password
      });
      
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      
      try {
        const userResponse = await axios.get(`${API_BASE}/api/auth/me`, {
          headers: { Authorization: `Bearer ${access_token}` }
        });
        setUser(userResponse.data);
      } catch (meError) {
        console.error('Error fetching user profile after login:', meError);
        // We don't block login if /me fails, but the user stays null
      }
      
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Login failed' 
      };
    }
  };

  const register = async (username, email, password) => {
    try {
      const response = await axios.post(`${API_BASE}/api/auth/register`, {
        username,
        email,
        password
      });
      
      if (response.data.verification_token) {
        localStorage.setItem('verification_token', response.data.verification_token);
      }
      
      return { success: true, data: response.data };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Registration failed' 
      };
    }
  };

  const verifyEmail = async (token) => {
    try {
      await axios.post(`${API_BASE}/api/auth/verify-email`, {
        token
      });
      setEmailSent(false);
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Email verification failed' 
      };
    }
  };

  const requestPasswordReset = async (email) => {
    try {
      await axios.post(`${API_BASE}/api/auth/request-password-reset`, {
        email
      });
      setResetEmailSent(true);
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Password reset request failed' 
      };
    }
  };

  const resetPassword = async (token, password) => {
    try {
      await axios.post(`${API_BASE}/api/auth/reset-password`, {
        token,
        password
      });
      return { success: true };
    } catch (error) {
      return { 
        success: false, 
        message: error.response?.data?.detail || 'Password reset failed' 
      };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('verification_token');
    setToken('');
    setUser(null);
    setEmailSent(false);
    setResetEmailSent(false);
  };

  const value = {
    user,
    loading,
    token,
    login,
    register,
    verifyEmail,
    requestPasswordReset,
    resetPassword,
    logout,
    emailSent,
    resetEmailSent
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
