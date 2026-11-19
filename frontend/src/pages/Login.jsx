import { useState } from 'react';
import { useAuth } from '../auth.jsx';
import { Link, navigate } from '../router.jsx';
import Logo from '../components/Logo.jsx';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="panel">
        <Link to="/" className="brand"><Logo size={34} /> Pearl Protocol</Link>
        <h1>Welcome back.</h1>
        <p style={{ color: 'var(--on-dark-muted)', lineHeight: 1.6, maxWidth: 420 }}>Sign in to review pipeline results, surveillance alerts and data quality.</p>
      </div>
      <div className="formside">
        <form onSubmit={submit} noValidate>
          <h2 style={{ fontFamily: 'var(--serif)', fontWeight: 500, fontSize: 30 }}>Sign in</h2>
          {error && <div className="err" role="alert">{error}</div>}
          <div className="field">
            <label htmlFor="u">Username</label>
            <input id="u" className="input" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="p">Password</label>
            <input id="p" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn" type="submit" disabled={busy || !username || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
        </form>
      </div>
    </div>
  );
}
