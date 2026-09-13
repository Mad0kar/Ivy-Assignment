import { useState } from 'react';
import { useAuth } from '../state/AuthContext';

const DEMOS = ['demo1@ivy.homes', 'demo2@ivy.homes', 'demo3@ivy.homes'];

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState(DEMOS[0]);
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      await signIn(email, password);
    } catch (e2) {
      setErr(e2 instanceof Error ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={submit}>
        <h1>Mumbai property explorer</h1>
        <p className="muted">
          Built on the Ivy Homes property API. Sign in with one of the demo accounts.
        </p>
        <label>
          Account
          <select value={email} onChange={(e) => setEmail(e.target.value)}>
            {DEMOS.map((d) => (
              <option key={d}>{d}</option>
            ))}
          </select>
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {err && <p className="error">{err}</p>}
        <button disabled={busy || !password}>{busy ? 'Signing in…' : 'Sign in'}</button>
        <p className="fineprint">
          Access tokens from this API last 15 minutes, not the 24 hours the
          documentation claims. The session refreshes itself in the background,
          so it stays usable well past that.
        </p>
      </form>
    </div>
  );
}
