# Fynvo v1.0.0 Known Limitations

Fynvo v1.0.0 is a stable-production baseline for the functionality already implemented in the Home Assistant add-on. The following capabilities are intentionally not claimed as delivered in v1.0.0 unless separately implemented and validated after this document was written.

## Deferred capabilities

- Production Open Banking / Consumer Data Right connectivity.
- Direct ING connectivity.
- Automatic production bank transaction synchronisation through a live provider.
- Production-grade automatic bank reconciliation.
- Advanced multi-user household administration and permissions.
- Immutable audit logs and complete user-activity reporting.
- Comprehensive per-record change history beyond the existing edit-history foundations.
- Home Assistant financial sensors/entities and automation-facing financial state.
- Standalone Cloudways or other non-Home-Assistant deployment.
- Advanced privacy and retention controls beyond the current local-first storage model.

## Operational acceptance

Some release gates depend on a real installed Home Assistant environment and cannot be proven by repository-level automated tests alone. In particular, final v1.0.0 acceptance should record the outcome of:

- installed add-on startup and restart;
- Home Assistant ingress navigation, login and browser refresh;
- iPhone-sized installed-app acceptance;
- representative upgrade from an existing v0.18.0 data set;
- backup and restore of persistent `/data` content.

If any of these checks have not been executed in a real Home Assistant environment, the release notes and pull request must state that they remain manual release gates rather than claiming they passed.

## Data storage

Fynvo is local-first. The Home Assistant add-on stores persistent application data under `/data`, including the SQLite database and Home Assistant add-on options made available to the container. Users should protect Home Assistant backups appropriately because they can contain sensitive household financial information.
