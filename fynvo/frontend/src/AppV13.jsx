import { useEffect, useRef, useState } from 'react';
import App from './App.jsx';
import LoginPage from './LoginPage.jsx';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

export default function AppV13() {
  const [auth, setAuth] = useState(null);
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
    const observer = new MutationObserver(() => {
      if (document.querySelector('main.login')) refreshAuth();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    observerRef.current = observer;
    return () => observer.disconnect();
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

  return <App />;
}
