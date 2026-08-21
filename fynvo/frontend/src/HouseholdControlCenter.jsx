import { useEffect, useMemo, useState } from 'react';

const api = (path, options = {}) => fetch(`api${path}`, {
  credentials: 'same-origin',
  headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  ...options,
});

const ROLE_LABELS = {
  administrator: 'Administrator',
  household_member: 'Household Member',
  read_only: 'Read Only',
};

async function readJson(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || 'The request could not be completed.');
  return payload;
}

export default function HouseholdControlCenter({ onClose, forcePasswordChange = false, onPasswordChanged }) {
  const [household, setHousehold] = useState(null);
  const [members, setMembers] = useState([]);
  const [security, setSecurity] = useState(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [editUserId, setEditUserId] = useState(null);
  const [secretNotice, setSecretNotice] = useState(null);
  const [householdName, setHouseholdName] = useState('');
  const [newMember, setNewMember] = useState({ username: '', display_name: '', role: 'household_member', temporary_password: '' });
  const [password, setPassword] = useState({ value: '', confirm: '' });

  const isAdmin = household?.role === 'administrator';
  const editingMember = useMemo(() => members.find((member) => member.user_id === editUserId) || null, [members, editUserId]);

  async function load() {
    setError('');
    const [householdResult, securityResult] = await Promise.all([
      api('/household/current').then(readJson),
      api('/household/me/security').then(readJson),
    ]);
    setHousehold(householdResult);
    setHouseholdName(householdResult.name || '');
    setSecurity(securityResult);
    if (householdResult.role === 'administrator') {
      const memberResult = await api('/household/members').then(readJson);
      setMembers(memberResult);
    } else {
      setMembers([]);
    }
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function run(action, successMessage) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const result = await action();
      if (successMessage) setNotice(successMessage);
      await load();
      return result;
    } catch (err) {
      setError(err.message);
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function saveHousehold(event) {
    event.preventDefault();
    await run(
      () => api('/household/current', { method: 'PUT', body: JSON.stringify({ name: householdName }) }).then(readJson),
      'Household details updated.',
    );
  }

  async function createMember(event) {
    event.preventDefault();
    const result = await run(
      () => api('/household/members', { method: 'POST', body: JSON.stringify(newMember) }).then(readJson),
      'Household member created.',
    );
    if (result) {
      setSecretNotice({ title: `Temporary password for ${result.display_name}`, value: result.temporary_password });
      setNewMember({ username: '', display_name: '', role: 'household_member', temporary_password: '' });
      setShowAdd(false);
    }
  }

  async function saveMember(event) {
    event.preventDefault();
    if (!editingMember) return;
    const form = new FormData(event.currentTarget);
    await run(
      () => api(`/household/members/${editingMember.user_id}`, {
        method: 'PUT',
        body: JSON.stringify({ display_name: form.get('display_name'), role: form.get('role') }),
      }).then(readJson),
      'Member updated.',
    );
    setEditUserId(null);
  }

  async function memberAction(member, action) {
    const result = await run(
      () => api(`/household/members/${member.user_id}/${action}`, { method: 'POST', body: '{}' }).then(readJson),
      action === 'deactivate' ? 'Member deactivated.' : action === 'reactivate' ? 'Member reactivated.' : 'Member security updated.',
    );
    if (result?.temporary_password) {
      setSecretNotice({ title: `Temporary password for ${member.display_name}`, value: result.temporary_password });
    }
  }

  async function changePassword(event) {
    event.preventDefault();
    if (password.value.length < 8) {
      setError('New password must be at least 8 characters.');
      return;
    }
    if (password.value !== password.confirm) {
      setError('The password confirmation does not match.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      await api('/household/me/change-temporary-password', {
        method: 'POST',
        body: JSON.stringify({ new_password: password.value }),
      }).then(readJson);
      setNotice('Password changed. Please sign in again.');
      if (onPasswordChanged) onPasswordChanged();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!household || !security) {
    return <main className="household-shell"><section className="household-panel" role="status">Loading Household settings…</section></main>;
  }

  if (forcePasswordChange || security.must_change_password) {
    return <main className="household-shell household-password-shell">
      <section className="household-panel household-password-card">
        <p className="eyebrow">Security</p>
        <h1>Choose your own password</h1>
        <p>Your administrator created a temporary credential. Set a private password before continuing into Fynvo.</p>
        {error && <div className="household-alert error" role="alert">{error}</div>}
        {notice && <div className="household-alert success" role="status">{notice}</div>}
        <form onSubmit={changePassword} className="household-form">
          <label>New password<input type="password" autoComplete="new-password" value={password.value} onChange={(event) => setPassword({ ...password, value: event.target.value })} required minLength={8}/></label>
          <label>Confirm password<input type="password" autoComplete="new-password" value={password.confirm} onChange={(event) => setPassword({ ...password, confirm: event.target.value })} required minLength={8}/></label>
          <button className="primary" type="submit" disabled={busy}>{busy ? 'Saving…' : 'Set password'}</button>
        </form>
      </section>
    </main>;
  }

  return <main className="household-shell">
    <section className="household-panel">
      <header className="household-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>Household</h1>
          <p>Manage the people who belong to this Fynvo household. Detailed financial permissions arrive in v1.3.0.</p>
        </div>
        {onClose && <button type="button" className="secondary" onClick={onClose}>Back to Fynvo</button>}
      </header>

      {error && <div className="household-alert error" role="alert">{error}</div>}
      {notice && <div className="household-alert success" role="status">{notice}</div>}
      {secretNotice && <div className="household-secret" role="status">
        <div><strong>{secretNotice.title}</strong><p>Shown once. Give this directly to the member and ask them to change it after signing in.</p></div>
        <code>{secretNotice.value}</code>
        <button type="button" onClick={() => navigator.clipboard?.writeText(secretNotice.value)}>Copy</button>
        <button type="button" className="secondary" onClick={() => setSecretNotice(null)}>Dismiss</button>
      </div>}

      <div className="household-summary-grid">
        <article><span>Household</span><strong>{household.name}</strong></article>
        <article><span>Your role</span><strong>{ROLE_LABELS[household.role] || household.role}</strong></article>
        <article><span>Active members</span><strong>{household.member_count}</strong></article>
        <article><span>MFA</span><strong>{security.mfa_enabled ? 'Enabled' : 'Not enabled'}</strong></article>
      </div>

      {isAdmin && <section className="household-section">
        <div className="household-section-heading"><div><h2>Household details</h2><p>The Household ID stays stable if the name changes.</p></div></div>
        <form className="household-inline-form" onSubmit={saveHousehold}>
          <label>Household name<input value={householdName} onChange={(event) => setHouseholdName(event.target.value)} maxLength={160} required/></label>
          <button type="submit" className="primary" disabled={busy}>Save</button>
        </form>
      </section>}

      {isAdmin && <section className="household-section">
        <div className="household-section-heading">
          <div><h2>Members</h2><p>Roles establish identity intent now. Full record visibility enforcement is intentionally deferred to v1.3.0.</p></div>
          <button type="button" className="primary" onClick={() => setShowAdd(true)}>Add member</button>
        </div>

        {showAdd && <form className="household-form member-form" onSubmit={createMember}>
          <h3>Add household member</h3>
          <label>Display name<input value={newMember.display_name} onChange={(event) => setNewMember({ ...newMember, display_name: event.target.value })} required/></label>
          <label>Username<input value={newMember.username} onChange={(event) => setNewMember({ ...newMember, username: event.target.value })} autoCapitalize="none" required/></label>
          <label>Role<select value={newMember.role} onChange={(event) => setNewMember({ ...newMember, role: event.target.value })}><option value="household_member">Household Member</option><option value="read_only">Read Only</option><option value="administrator">Administrator</option></select></label>
          <label>Temporary password <span className="optional">optional</span><input type="password" value={newMember.temporary_password} onChange={(event) => setNewMember({ ...newMember, temporary_password: event.target.value })} placeholder="Generate securely if blank"/></label>
          <div className="household-actions"><button type="submit" className="primary" disabled={busy}>Create member</button><button type="button" className="secondary" onClick={() => setShowAdd(false)}>Cancel</button></div>
        </form>}

        <div className="household-member-list">
          {members.map((member) => <article className="household-member-card" key={member.user_id}>
            <div className="household-member-main">
              <div><strong>{member.display_name}</strong><span>@{member.username}</span></div>
              <div className="household-badges"><span>{ROLE_LABELS[member.role]}</span><span className={member.status === 'active' ? 'active' : 'inactive'}>{member.status}</span>{member.mfa_enabled && <span>MFA</span>}{member.must_change_password && <span>Temporary password</span>}</div>
            </div>
            <div className="household-actions wrap">
              <button type="button" onClick={() => setEditUserId(member.user_id)}>Edit</button>
              {member.status === 'active' ? <button type="button" onClick={() => memberAction(member, 'deactivate')}>Deactivate</button> : <button type="button" onClick={() => memberAction(member, 'reactivate')}>Reactivate</button>}
              <button type="button" onClick={() => memberAction(member, 'password-reset')}>Reset password</button>
              {member.mfa_enabled && <button type="button" onClick={() => memberAction(member, 'mfa-reset')}>Reset MFA</button>}
              <button type="button" onClick={() => memberAction(member, 'sessions/revoke')}>Revoke sessions</button>
            </div>
          </article>)}
        </div>
      </section>}

      {!isAdmin && <section className="household-section"><h2>Your membership</h2><p>You belong to <strong>{household.name}</strong> as a <strong>{ROLE_LABELS[household.role]}</strong>. Household administration is restricted to Administrators.</p></section>}

      {editingMember && <div className="household-modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setEditUserId(null); }}>
        <section className="household-modal" role="dialog" aria-modal="true" aria-labelledby="edit-member-title">
          <h2 id="edit-member-title">Edit {editingMember.display_name}</h2>
          <form onSubmit={saveMember} className="household-form">
            <label>Display name<input name="display_name" defaultValue={editingMember.display_name} required/></label>
            <label>Role<select name="role" defaultValue={editingMember.role}><option value="household_member">Household Member</option><option value="read_only">Read Only</option><option value="administrator">Administrator</option></select></label>
            <p className="household-help">Fynvo will block changes that would leave the Household without an active Administrator.</p>
            <div className="household-actions"><button className="primary" type="submit" disabled={busy}>Save member</button><button className="secondary" type="button" onClick={() => setEditUserId(null)}>Cancel</button></div>
          </form>
        </section>
      </div>}
    </section>
  </main>;
}
