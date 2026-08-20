import { useEffect, useRef, useState } from 'react';
import logo from './assets/fynvo-logo.svg';
import mark from './assets/fynvo-mark.svg';
import './auth-v13.css';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

function UserIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0"/></svg>;
}

function LockIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>;
}

function EyeIcon({ hidden }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.5"/>{hidden && <path d="m4 4 16 16"/>}</svg>;
}

function ArrowIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6"/></svg>;
}

function ShieldIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5 6v5c0 4.8 2.8 8.3 7 10 4.2-1.7 7-5.2 7-10V6l-7-3Z"/></svg>;
}

function ForecastIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 17 5-5 3 3 7-8"/><path d="M15 7h4v4"/></svg>;
}

function WalletIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h14a2 2 0 0 1 2 2v9H6a2 2 0 0 1-2-2V7Z"/><path d="M4 7V5a2 2 0 0 1 2-2h11v4M15 12h5"/></svg>;
}

function Feature({ icon, title, children }) {
  return <div className="fynvo-auth-feature"><span className="fynvo-auth-feature-icon">{icon}</span><div><h3>{title}</h3><p>{children}</p></div></div>;
}

function getErrorMessage(response, payload) {
  if (response.status === 401) return payload?.detail || 'Invalid username, password or verification code.';
  if (response.status === 403) return 'This account is currently disabled.';
  if (response.status === 428) return 'Administrator account has not been configured.';
  if (response.status === 429) return 'Too many sign-in attempts. Please wait and try again.';
  if (payload?.detail && typeof payload.detail === 'string') return payload.detail;
  return 'We could not connect to the authentication service. Please try again.';
}

export default function LoginPage({ authState, onAuthenticated, onStateRefresh }) {
  const setupMode = Boolean(authState?.setup_required);
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mfaChallenge, setMfaChallenge] = useState(null);
  const [mfaCode, setMfaCode] = useState('');
  const usernameRef = useRef(null);
  const mfaRef = useRef(null);

  useEffect(() => {
    if (mfaChallenge) mfaRef.current?.focus();
    else usernameRef.current?.focus();
  }, [mfaChallenge]);

  async function submitMfa(event) {
    event.preventDefault();
    if (loading) return;
    const code = mfaCode.trim();
    if (!code) { setError('Enter your authenticator or recovery code.'); return; }
    setLoading(true);
    setError('');
    try {
      const response = await api('/v11/auth/mfa-challenge', {
        method: 'POST',
        body: JSON.stringify({ challenge_token: mfaChallenge.challenge_token, code }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setError(getErrorMessage(response, body));
        return;
      }
      setMfaCode('');
      setMfaChallenge(null);
      await onAuthenticated?.(body);
    } catch {
      setError('We could not complete MFA verification. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    if (loading) return;
    setError('');
    const cleanUsername = username.trim();
    if (!cleanUsername) { setError('Username is required.'); return; }
    if (!password) { setError('Password is required.'); return; }
    if (setupMode && password !== confirmPassword) { setError('Passwords do not match.'); return; }

    setLoading(true);
    try {
      const endpoint = setupMode ? '/auth/setup' : '/auth/login';
      const payload = setupMode
        ? { username: cleanUsername, display_name: displayName.trim() || cleanUsername, password }
        : { username: cleanUsername, password };
      const response = await api(endpoint, { method: 'POST', body: JSON.stringify(payload) });
      const body = await response.json().catch(() => null);
      if (!response.ok) {
        setError(getErrorMessage(response, body));
        if (response.status === 428) await onStateRefresh?.();
        return;
      }
      if (body?.mfa_required) {
        setMfaChallenge(body);
        setPassword('');
        setConfirmPassword('');
        return;
      }
      setPassword('');
      setConfirmPassword('');
      await onAuthenticated?.(body);
    } catch {
      setError('We could not connect to the authentication service. Please try again.');
    } finally {
      setLoading(false);
    }
  }

  const challengeForm = <form className="fynvo-auth-card" onSubmit={submitMfa} noValidate>
    <img className="fynvo-auth-card-logo" src={logo} alt="Fynvo"/>
    <div className="fynvo-auth-heading"><h2>Two-step verification</h2><p>Enter the 6-digit code from your authenticator, or one of your Fynvo recovery codes.</p></div>
    {error && <div className="fynvo-auth-error" role="alert"><strong>Verification failed</strong><span>{error}</span></div>}
    <label className="fynvo-auth-field"><span>Verification code</span><div className="fynvo-auth-input"><i><ShieldIcon/></i><input ref={mfaRef} name="mfa-code" autoComplete="one-time-code" inputMode="numeric" value={mfaCode} onChange={(event) => setMfaCode(event.target.value)} placeholder="123456 or recovery code" disabled={loading}/></div></label>
    <button className="fynvo-auth-submit" type="submit" disabled={loading} aria-busy={loading}>{loading ? 'Verifying…' : 'Verify and sign in'}{!loading && <ArrowIcon/>}</button>
    <button className="fynvo-auth-secondary" type="button" disabled={loading} onClick={() => { setMfaChallenge(null); setMfaCode(''); setError(''); }}>Back to sign in</button>
  </form>;

  return <main className="fynvo-auth-page">
    <section className="fynvo-auth-brand-panel" aria-label="Fynvo"><div className="fynvo-auth-brand-inner"><div className="fynvo-auth-brand-lockup"><img src={mark} alt=""/><strong>Fynvo</strong></div><div className="fynvo-auth-brand-copy"><h1>Know what's<br className="desktop-only"/> coming<span>.</span></h1><p>Plan today. See what's ahead.<br/>Fynvo helps you forecast, budget and stay in control of your financial future.</p></div><div className="fynvo-auth-features"><Feature icon={<ForecastIcon/>} title="Forecast with confidence">See your future cash flow and plan ahead.</Feature><Feature icon={<WalletIcon/>} title="Budget smarter">Stay on track with budgets that work for you.</Feature><Feature icon={<ShieldIcon/>} title="Financial clarity">All your finances in one place, clear and simple.</Feature></div><div className="fynvo-auth-chart" aria-hidden="true"><i/><i/><i/><i/><i/><i/><i/><i/></div></div></section>
    <section className="fynvo-auth-form-panel">
      <div className="fynvo-auth-mobile-intro"><img src={mark} alt="Fynvo"/><strong>Fynvo</strong><h1>Know what's coming<span>.</span></h1><p>Plan today. See what's ahead.</p></div>
      {mfaChallenge ? challengeForm : <form className="fynvo-auth-card" onSubmit={submit} noValidate>
        <img className="fynvo-auth-card-logo" src={logo} alt="Fynvo"/>
        <div className="fynvo-auth-heading"><h2>{setupMode ? 'Create administrator' : 'Welcome back'}</h2><p>{setupMode ? 'Create your Fynvo administrator account.' : 'Sign in to access your financial overview.'}</p></div>
        {authState?.message && <div className="fynvo-auth-notice" role="status">{authState.message}</div>}
        {error && <div className="fynvo-auth-error" role="alert"><strong>Unable to sign in</strong><span>{error}</span></div>}
        <label className="fynvo-auth-field"><span>Username</span><div className="fynvo-auth-input"><i><UserIcon/></i><input ref={usernameRef} name="username" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Enter your username" disabled={loading}/></div></label>
        {setupMode && <label className="fynvo-auth-field"><span>Display name</span><div className="fynvo-auth-input"><i><UserIcon/></i><input name="name" autoComplete="name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} placeholder="Enter your display name" disabled={loading}/></div></label>}
        <label className="fynvo-auth-field"><span>Password</span><div className="fynvo-auth-input"><i><LockIcon/></i><input name="password" type={showPassword ? 'text' : 'password'} autoComplete={setupMode ? 'new-password' : 'current-password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Enter your password" disabled={loading}/><button type="button" className="fynvo-auth-eye" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'} disabled={loading}><EyeIcon hidden={showPassword}/></button></div></label>
        {setupMode && <label className="fynvo-auth-field"><span>Confirm password</span><div className="fynvo-auth-input"><i><LockIcon/></i><input name="confirm-password" type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm your password" disabled={loading}/></div></label>}
        <button className="fynvo-auth-submit" type="submit" disabled={loading} aria-busy={loading}>{loading ? 'Signing in…' : setupMode ? 'Create Administrator Account' : 'Sign in'}{!loading && <ArrowIcon/>}</button>
      </form>}
      <div className="fynvo-auth-security"><ShieldIcon/><div><strong>Your data is secure with Fynvo</strong><p>Your financial data and authentication are protected by Fynvo's server-side access controls and optional authenticator-based MFA.</p></div></div>
    </section>
  </main>;
}
