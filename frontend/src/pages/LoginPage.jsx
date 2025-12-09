import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Footer from '../components/Footer';
import BrandLogo from '../components/BrandLogo';
import './Auth.css';
import './BackButton.css';

export default function LoginPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
        const result = await api.login(email, password);
        // Save token or handle success, for now just redirect
        navigate('/dashboard', { state: { user: result.user } });
    } catch (err) {
        alert(err.message || "Login Failed");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <BrandLogo />

      <div className="auth-card login-theme">
        <h2 className="auth-title login">
          Access Dashboard
        </h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="form-input"
              placeholder="manager@mcdonalds.com"
            />
          </div>

          <div className="form-group">
             <label className="form-label">Password</label>
             <input 
               type="password" 
               value={password}
               onChange={(e) => setPassword(e.target.value)}
               required
               className="form-input"
             />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="btn-submit btn-submit-login"
          >
            {loading ? 'Authenticating...' : 'Login'}
          </button>
        </form>
         <p className="auth-footer">
          New terminal? <span onClick={() => navigate('/register')} className="link-text">Register</span>
        </p>
      </div>
      <Footer />
    </div>
  );
}
