from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


def run_migrations() -> None:
    from .models import Account, AppConfig, LoginAttempt, Session, Transaction, Transfer, User

    engine = get_engine()
    Base.metadata.create_all(bind=engine, tables=[User.__table__, Session.__table__, LoginAttempt.__table__, AppConfig.__table__, Account.__table__, Transfer.__table__, Transaction.__table__])
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)"))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS income_sources (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                amount_cents INTEGER, frequency VARCHAR(40), interval_count INTEGER,
                next_payment_date DATE, destination_account_id INTEGER, payer VARCHAR(140),
                category VARCHAR(80), owner_group VARCHAR(80), is_active BOOLEAN NOT NULL DEFAULT 1,
                start_date DATE, end_date DATE, notes TEXT, source VARCHAR(40) NOT NULL DEFAULT 'manual',
                created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(destination_account_id) REFERENCES accounts(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS recurring_expenses (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                amount_cents INTEGER, frequency VARCHAR(40), interval_count INTEGER, next_due_date DATE,
                direct_debit BOOLEAN, account_id INTEGER, source_account_text VARCHAR(140), category VARCHAR(80),
                expense_type VARCHAR(80), owner_group VARCHAR(80), is_active BOOLEAN NOT NULL DEFAULT 1,
                variable_amount BOOLEAN NOT NULL DEFAULT 0, aliases TEXT, notes TEXT, last_paid_date DATE,
                source VARCHAR(40) NOT NULL DEFAULT 'manual', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, recurring_expense_id INTEGER,
                name VARCHAR(140) NOT NULL, provider VARCHAR(140), bill_type VARCHAR(80), priority VARCHAR(20) NOT NULL DEFAULT 'normal',
                original_status VARCHAR(80), original_amount_cents INTEGER, remaining_amount_cents INTEGER,
                due_date DATE, pay_cycle_date DATE, account_id INTEGER, source_account_text VARCHAR(140), paid_through_date DATE,
                notes TEXT, is_active BOOLEAN NOT NULL DEFAULT 1, resolved_at DATETIME, paid_at DATETIME,
                source VARCHAR(40) NOT NULL DEFAULT 'manual', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(recurring_expense_id) REFERENCES recurring_expenses(id), FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS planned_spending (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                description TEXT, estimated_amount_cents INTEGER, planned_date DATE, start_date DATE, end_date DATE,
                category VARCHAR(80), account_id INTEGER, merchant VARCHAR(140), priority VARCHAR(20) NOT NULL DEFAULT 'medium',
                status VARCHAR(40) NOT NULL DEFAULT 'wishlist', owner_group VARCHAR(80), include_in_forecast BOOLEAN NOT NULL DEFAULT 1,
                is_recurring BOOLEAN NOT NULL DEFAULT 0, notes TEXT, archived_at DATETIME, purchased_at DATETIME,
                source VARCHAR(40) NOT NULL DEFAULT 'manual', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS effective_amount_changes (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, record_type VARCHAR(40) NOT NULL,
                record_id INTEGER NOT NULL, new_amount_cents INTEGER NOT NULL,
                effective_from DATE NOT NULL, effective_to DATE, source VARCHAR(80),
                notes TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS forecast_scenarios (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                description TEXT, payload TEXT NOT NULL, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                parent_id INTEGER, icon VARCHAR(40), color VARCHAR(40), category_type VARCHAR(40) NOT NULL DEFAULT 'expense',
                budget_relationship VARCHAR(40) NOT NULL DEFAULT 'independent', is_active BOOLEAN NOT NULL DEFAULT 1,
                notes TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(parent_id) REFERENCES categories(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, name VARCHAR(140) NOT NULL,
                category_id INTEGER, category_name VARCHAR(140), direction VARCHAR(20) NOT NULL DEFAULT 'expense',
                period VARCHAR(20) NOT NULL DEFAULT 'monthly', amount_cents INTEGER NOT NULL,
                allocation_strategy VARCHAR(40) NOT NULL DEFAULT 'spend_during_period',
                relationship_mode VARCHAR(40) NOT NULL DEFAULT 'independent', anchor_date DATE NOT NULL,
                start_date DATE NOT NULL, end_date DATE, rollover_enabled BOOLEAN NOT NULL DEFAULT 0,
                negative_rollover_enabled BOOLEAN NOT NULL DEFAULT 0, rollover_cents INTEGER NOT NULL DEFAULT 0,
                notes TEXT, is_active BOOLEAN NOT NULL DEFAULT 1, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(category_id) REFERENCES categories(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS budget_versions (
                id INTEGER PRIMARY KEY, budget_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
                amount_cents INTEGER NOT NULL, period VARCHAR(20) NOT NULL,
                allocation_strategy VARCHAR(40) NOT NULL, effective_from DATE NOT NULL,
                effective_to DATE, created_at DATETIME NOT NULL,
                FOREIGN KEY(budget_id) REFERENCES budgets(id), FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS saved_views (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, screen VARCHAR(80) NOT NULL,
                name VARCHAR(140) NOT NULL DEFAULT 'Default', settings_json TEXT NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS edit_history (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, record_type VARCHAR(80) NOT NULL,
                record_id INTEGER NOT NULL, original_json TEXT NOT NULL, updated_json TEXT NOT NULL,
                source VARCHAR(40) NOT NULL DEFAULT 'ui', created_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS import_profiles (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, source_name VARCHAR(180) NOT NULL,
                mapping_json TEXT NOT NULL, updated_at DATETIME NOT NULL,
                UNIQUE(user_id, source_name), FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS import_batches (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, filename VARCHAR(180) NOT NULL,
                account_id INTEGER NOT NULL, row_count INTEGER NOT NULL DEFAULT 0,
                imported_count INTEGER NOT NULL DEFAULT 0, skipped_count INTEGER NOT NULL DEFAULT 0,
                duplicate_count INTEGER NOT NULL DEFAULT 0, matched_count INTEGER NOT NULL DEFAULT 0,
                failed_count INTEGER NOT NULL DEFAULT 0, status VARCHAR(40) NOT NULL DEFAULT 'complete',
                created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        """))
        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS reconciliation_links (
                id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, transaction_id INTEGER NOT NULL,
                source_type VARCHAR(60) NOT NULL, source_id INTEGER NOT NULL,
                expected_amount_cents INTEGER NOT NULL DEFAULT 0, actual_amount_cents INTEGER NOT NULL DEFAULT 0,
                variance_cents INTEGER NOT NULL DEFAULT 0, status VARCHAR(40) NOT NULL DEFAULT 'suggested_match',
                confidence INTEGER NOT NULL DEFAULT 0, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id), FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
        """))
        current = connection.execute(text("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")).scalar()
        if current is None:
            connection.execute(text("INSERT INTO schema_version (version) VALUES (8)"))
        elif current < 8:
            connection.execute(text("UPDATE schema_version SET version = 8"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_account_date ON transactions(account_id, transaction_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_user_type ON transactions(user_id, transaction_type)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_source ON transactions(source)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_user_category_date ON transactions(user_id, category, transaction_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_transactions_import ON transactions(user_id, import_batch_id, external_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_income_user_next ON income_sources(user_id, next_payment_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_recurring_user_next ON recurring_expenses(user_id, next_due_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_recurring_user_active ON recurring_expenses(user_id, is_active)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_bills_user_due ON bills(user_id, due_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_bills_priority ON bills(priority)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_planned_user_date ON planned_spending(user_id, planned_date)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_planned_user_status ON planned_spending(user_id, status)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_planned_forecast ON planned_spending(user_id, include_in_forecast)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_effective_changes_record ON effective_amount_changes(user_id, record_type, record_id, effective_from)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_scenarios_user ON forecast_scenarios(user_id, name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_categories_user_parent ON categories(user_id, parent_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_budgets_user_category ON budgets(user_id, category_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_budget_versions_effective ON budget_versions(budget_id, effective_from)"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_saved_views_unique ON saved_views(user_id, screen, name)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_import_batches_user ON import_batches(user_id, created_at)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS idx_reconciliation_review ON reconciliation_links(user_id, status, confidence)"))


def reset_database_for_tests() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        Base.metadata.drop_all(bind=_engine)
        _engine.dispose()
    _engine = None
    _SessionLocal = None
    get_settings.cache_clear()
