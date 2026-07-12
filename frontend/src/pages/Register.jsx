import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../api';

export default function Register() {
  const [form, setForm] = useState({ email: '', username: '', password: '', password_confirm: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/auth/register/', form);
      const loginRes = await api.post('/auth/login/', { email: form.email, password: form.password });
      localStorage.setItem('access_token', loginRes.data.access);
      localStorage.setItem('refresh_token', loginRes.data.refresh);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      if (typeof data === 'object') {
        setError(Object.values(data).flat().join(' '));
      } else {
        setError('Registration failed');
      }
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Fair Share</h1>
        <p className="subtitle">Create your account</p>
        <form onSubmit={handleSubmit}>
          {error && <div className="error-msg">{error}</div>}
          <input name="email" type="email" placeholder="Email" value={form.email} onChange={handleChange} required />
          <input name="username" type="text" placeholder="Username" value={form.username} onChange={handleChange} required />
          <input name="password" type="password" placeholder="Password" value={form.password} onChange={handleChange} required />
          <input name="password_confirm" type="password" placeholder="Confirm Password" value={form.password_confirm} onChange={handleChange} required />
          <button type="submit">Register</button>
        </form>
        <p className="switch-link">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}
