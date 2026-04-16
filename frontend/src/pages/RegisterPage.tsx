import { useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import toast from 'react-hot-toast';

const ROLE_OPTIONS = [
  { value: 'viewer', label: 'Viewer — watch tournaments & auctions' },
  { value: 'team_owner', label: 'Team Owner — bid and manage a team' },
  { value: 'organizer', label: 'Organizer — create tournaments & matches' },
];

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('viewer');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { toast.error('Password must be at least 6 characters'); return; }
    setLoading(true);
    try {
      await register(email, password, fullName, [role]);
      toast.success('Account created! Welcome to BidWicket 🏏');
      navigate('/');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card fade-in">
        <div className="auth-logo">
          <div style={{ fontSize: '2.5rem' }}>🏏</div>
          <div style={{ fontSize: '1.4rem', fontWeight: 800, marginTop: '0.5rem' }}>
            Bid<span style={{ color: 'var(--accent-light)' }}>Wicket</span>
          </div>
        </div>

        <h1 className="auth-title">Create account</h1>
        <p className="auth-subtitle">Join the cricket auction revolution</p>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input id="reg-name" type="text" placeholder="Virat Kohli" value={fullName}
              onChange={e => setFullName(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Email</label>
            <input id="reg-email" type="email" placeholder="you@example.com" value={email}
              onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input id="reg-password" type="password" placeholder="Min. 6 characters" value={password}
              onChange={e => setPassword(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Role</label>
            <select id="reg-role" value={role} onChange={e => setRole(e.target.value)}>
              {ROLE_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>

          <button id="reg-submit" type="submit" className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: '0.5rem' }} disabled={loading}>
            {loading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <div className="divider" />
        <p className="text-muted text-sm" style={{ textAlign: 'center' }}>
          Already have an account?{' '}
          <Link to="/login" style={{ color: 'var(--accent-light)', fontWeight: 600 }}>Sign in</Link>
        </p>
      </div>
    </div>
  );
}
