import { useEffect, useRef, useState } from 'react';
import App from './AppCorrectiveV0174.jsx';
import LoginPage from './LoginPage.jsx';
import V11ControlCenter from './V11ControlCenter.jsx';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

export default function AppV13() {
  const [auth, setAuth] = useState(null);
  const [recoveryWarningDismissed, setRecoveryWarningDismissed] = useState(false);
  const [v11Mode, setV11Mode] = useState(null);
  const observerRef = useRef(null);

  async function refreshAuth() {
    try {
      const response = await api('/auth/state');
      if (!response.ok) throw new Error('auth-state');
      const state = await response.json();
      setAuth(state);
      return state;
    } catch {
      setAuth({ authenticated: false, setup_required: false, user: null, message: 'Authentication service unavailable.' });
      return null;
    }
  }

  useEffect(() => { refreshAuth(); }, []);

  useEffect(() => {
    if (!auth?.authenticated) return undefined;
    const syncPageClass = () => {
      const heading = document.querySelector('main.content .header h1')?.textContent?.trim();
      document.body.classList.toggle('fynvo-income-page', heading === 'Income');
    };
    const observer = new MutationObserver(() => {
      syncPageClass();
      if (document.querySelector('main.login')) refreshAuth();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    observerRef.current = observer;
    syncPageClass();
    return () => {
      observer.disconnect();
      document.body.classList.remove('fynvo-income-page');
    };
  }, [auth?.authenticated]);

  if (!auth) {
    return <main className="fynvo-auth-page"><section className="fynvo-auth-form-panel"><div className="fynvo-auth-card" role="status">Loading Fynvo…</div></section></main>;
  }

  if (!auth.authenticated) {
    return <LoginPage
      authState={auth}
      onStateRefresh={refreshAuth}
      onAuthenticated={async () => { await refreshAuth(); }}
    />;
  }

  if (v11Mode) {
    return <V11ControlCenter mode={v11Mode} onClose={() => setV11Mode(null)}/>;
  }

  return <>
    {auth.recovery_mode && !recoveryWarningDismissed && (
      <div className="fynvo-recovery-warning" role="status" aria-live="polite">
        <span><strong>Administrator recovery mode is enabled.</strong> Confirm this login works, then disable <code>admin_recovery_mode</code> in the Home Assistant add-on Configuration page and restart Fynvo.</span>
        <button type="button" onClick={() => setRecoveryWarningDismissed(true)} aria-label="Dismiss administrator recovery warning">Dismiss</button>
      </div>
    )}
    <App />
    <nav className="v11-launcher" aria-label="Fynvo v1.1 data and security tools">
      <button type="button" onClick={() => setV11Mode('coverage')}>Data Coverage</button>
      <button type="button" onClick={() => setV11Mode('splits')}>Split Transaction</button>
      <button type="button" onClick={() => setV11Mode('security')}>Security & MFA</button>
      <button type="button" onClick={() => setV11Mode('export')}>Data Export</button>
    </nav>
  </>;
}
