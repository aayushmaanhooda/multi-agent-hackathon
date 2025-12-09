import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import Footer from '../components/Footer';
import BrandLogo from '../components/BrandLogo';
import './Auth.css';
import './BackButton.css';

export default function RegisterPage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'employee',
    access_code: ''
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
        const result = await api.register(formData);
        alert("Registration Successful! Please Login.");
        navigate('/login');
    } catch (err) {
        alert(err.message || "Registration Failed");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <BrandLogo />

      <div className="auth-card register-theme">
        <h2 className="auth-title register">
          Join the Network
        </h2>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input 
              type="text" 
              name="name"
              required
              className="form-input"
              placeholder="John Doe"
              value={formData.name}
              onChange={handleChange}
            />
          </div>
          
          <div className="form-group">
            <label className="form-label">Email</label>
            <input 
              type="email" 
              name="email"
              required
              className="form-input"
              placeholder="manager@mcdonalds.com"
              value={formData.email}
              onChange={handleChange}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Role</label>
            <select 
                name="role" 
                className="form-input" 
                value={formData.role} 
                onChange={handleChange}
            >
                <option value="employee">Employee</option>
                <option value="admin">Admin</option>
            </select>
          </div>

          {formData.role === 'admin' && (
              <div className="form-group">
                <label className="form-label">Admin Access Code</label>
                <input 
                  type="password" 
                  name="access_code"
                  required
                  className="form-input"
                  placeholder="Enter Admin Code"
                  value={formData.access_code}
                  onChange={handleChange}
                />
              </div>
          )}

          <div className="form-group">
             <label className="form-label">Password</label>
             <input 
               type="password" 
               name="password"
               required
               className="form-input"
               value={formData.password}
               onChange={handleChange}
             />
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="btn-submit btn-submit-register"
          >
            {loading ? 'Processing...' : 'Register'}
          </button>
        </form>
        
        <p className="auth-footer">
          Already have an account? <span onClick={() => navigate('/login')} className="link-text">Login</span>
        </p>
      </div>
      <Footer />
    </div>
  );
}
