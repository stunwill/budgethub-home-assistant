# Fynvo Installation and Manual Verification

## Repository

Use the renamed repository:

```text
https://github.com/stunwill/fynvo-home-assistant
```

## First run

1. Install the Fynvo add-on in Home Assistant.
2. Start the add-on.
3. Open the Web UI.
4. Create the first administrator account.
5. Sign in.
6. Confirm the Overview dashboard loads.

## v0.3.0 manual Home Assistant verification

Use this as the release-blocking manual test:

```text
Home Assistant
→ Settings
→ Add-ons
→ Fynvo
→ Open Web UI
→ Fynvo login loads
→ Login succeeds
→ Overview dashboard loads
→ Accounts loads
→ Transactions load
→ Refreshing the browser continues to work
```

Also verify any configured Home Assistant sidebar entry opens Fynvo.

Expected backend health endpoint:

```text
/api/health
```

This endpoint must not require authentication and should return the current Fynvo version.
