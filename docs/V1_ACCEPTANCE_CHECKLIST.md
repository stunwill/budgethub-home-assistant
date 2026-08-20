# Fynvo v1.0.0 Acceptance Checklist

This checklist separates repository-verifiable gates from installed Home Assistant/manual gates. Do not mark a manual gate complete unless it has actually been executed.

## Automated / repository-verifiable gates

- [ ] Backend Python compilation passes.
- [ ] Ruff passes.
- [ ] Complete backend test suite passes.
- [ ] Application import/startup validation passes.
- [ ] Frontend regression tests pass.
- [ ] Frontend production build passes.
- [ ] Home Assistant YAML/metadata validation passes.
- [ ] Docker image build passes.
- [ ] Fresh database migration to the current schema passes.
- [ ] Representative v0.18.0 upgrade fixture passes without data loss.
- [ ] Representative older v0.x upgrade fixture passes without data loss.
- [ ] Category duplicate-prevention, merge and integrity tests pass.
- [ ] Account/Card integrity tests pass.
- [ ] Account, transaction, transfer and liability calculations pass.
- [ ] Income, recurring expense, bill, planned spending and commitment regressions pass.
- [ ] Forecast and budget calculation fixtures pass.
- [ ] CSV repeat-import duplicate protection passes.
- [ ] Reconciliation-link integrity tests pass.
- [ ] Authentication bootstrap, login, logout, session and recovery tests pass.
- [ ] Version metadata consistently reports 1.0.0.

## Installed Home Assistant / manual release gates

- [ ] Install/update Fynvo in Home Assistant successfully.
- [ ] Start and restart the add-on successfully.
- [ ] Open Fynvo through Home Assistant ingress.
- [ ] Login and logout through ingress.
- [ ] Refresh and directly navigate application routes through ingress.
- [ ] Confirm frontend assets and API requests work through ingress.
- [ ] Confirm persistent data survives add-on restart.
- [ ] Upgrade a representative v0.18.0 installed data set to v1.0.0.
- [ ] Validate an iPhone-sized installed-app workflow across major pages.
- [ ] Validate a representative tablet/desktop workflow.
- [ ] Complete a Home Assistant backup containing Fynvo data.
- [ ] Restore that backup and verify representative financial records and authentication.

## Sign-off rule

If any manual gate cannot be executed in the development environment, leave it unchecked and record it explicitly in the pull request/release notes as a remaining manual release gate. Do not claim it passed based solely on source-level or container tests.
