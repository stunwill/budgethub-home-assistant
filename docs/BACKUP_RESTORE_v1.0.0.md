# Fynvo v1.0.0 Backup and Restore

Fynvo runs as a Home Assistant add-on and stores persistent application state under `/data` inside the add-on environment. The authoritative financial database is the SQLite database configured by `FYNVO_DATABASE_URL`, which defaults to `/data/fynvo.sqlite3`.

## Recommended backup method

Use a Home Assistant backup that includes Fynvo add-on data. Treat that backup as sensitive because it can contain household financial records and authentication data.

Before a release or manual migration:

1. Stop Fynvo or otherwise ensure the database is not being actively modified.
2. Create a Home Assistant backup that includes the Fynvo add-on and its data.
3. Confirm the backup completed successfully before upgrading or performing data-repair work.
4. Restart Fynvo if it was stopped.

## Restore validation procedure

For a representative acceptance test:

1. Create or identify representative Fynvo data covering Accounts, Transactions, Categories, Recurring Expenses, Bills, Income, Planned Spending, Budgets and Goals.
2. Create a Home Assistant backup containing Fynvo data.
3. Record a small set of expected values, for example Account balances, Category names and counts of core records.
4. Modify or delete test records after the backup.
5. Restore the Home Assistant backup containing the Fynvo add-on data.
6. Restart Fynvo.
7. Verify authentication works.
8. Verify the recorded Accounts, Transactions, Categories, Recurring Expenses, Bills, Income, Planned Spending, Budgets, Goals and settings have returned to the expected state.
9. Verify `/api/health` responds successfully and reports the expected release version.

## Important constraints

- Do not restore individual SQLite files over a running Fynvo process.
- Do not reset or recreate the database as part of normal upgrade or recovery.
- Do not treat a repository-level database-copy unit test as proof that the installed Home Assistant backup/restore path works. The installed add-on restore must be recorded separately as a manual release gate when it cannot be executed in the development environment.
