# Fynvo v1.0.0 Readiness Assessment after v0.17.0

## Recommendation

**NOT READY FOR v1.0.0 until the manual Home Assistant acceptance gates below pass.**

The automated v0.17.0 hardening work addresses the release-blocking Account creation defect and strengthens account semantics, balance calculations, transfer behaviour, mobile navigation safeguards and regression coverage. However, a stable v1.0.0 label requires real installed-add-on validation, upgrade validation against household data, and backup/restore validation.

## BLOCKER

- Complete the v0.17.0 Account creation release gate through the installed Home Assistant add-on: create `Kristy - Main AC`, reload, restart Fynvo, logout/login and confirm persistence.
- Complete the iPhone/Home Assistant ingress navigation gate: drawer closed by default, opens from hamburger, closes on destination/backdrop, background scroll locked.
- Complete a representative v0.16.0 to v0.17.0 upgrade using a copy/backup of real data and verify no record loss or orphaned relationships.
- Complete backup and restore validation before stable v1.0.0 tagging.

## HIGH

- Run the full core CRUD smoke workflow through the actual UI, including Accounts, Transactions, Income, Recurring Expenses, Bills, Planned Spending, Categories, Budgets, Goals and Scenarios.
- Validate Cash Flow, Budget and Forecast values against representative known household data after the account-model changes.
- Validate mobile modal behaviour with the iOS keyboard in the Home Assistant mobile webview.
- Confirm authentication bootstrap, configured administrator recovery, recovery-disabled restart, session persistence and logout in the installed add-on.

## MEDIUM

- Broaden browser-driven end-to-end tests beyond the current source-contract responsive tests when the repository adopts a browser test runner.
- Review category parent assignment/cycle prevention and expose clearer hierarchy controls where the existing backend supports them.
- Review archive management UI so historical Accounts can be inspected/reactivated without exposing archived Accounts in ordinary selectors.
- Add stronger loading-state differentiation in data-heavy pages. The current application still treats some failed list requests as empty arrays.
- Review large-history performance using representative transaction volumes.

## LOW

- Continue refining compact mobile page actions and user/account menu placement.
- Improve account icons/visual differentiation by type.
- Expand user-facing help text for asset/liability and offset-account semantics.

## Known scope limitation

The merged v0.16.0 repository does not contain the previously proposed Home Assistant financial sensor/entity implementation. Fynvo remains a Home Assistant ingress add-on, but v0.17.0 cannot regression-test financial entities/actions that are not present in the merged source. This must not be represented as delivered v1.0.0 functionality unless it is actually implemented and tested in a later release.

## Stable-release handoff

Once BLOCKER and HIGH acceptance items pass, v1.0.0 should remain a controlled stable-release process focused on final QA, migration/upgrade validation, backup/restore, security review, documentation, production packaging, known limitations, final acceptance defects, release notes and stable tagging. It should not become another large feature release.
