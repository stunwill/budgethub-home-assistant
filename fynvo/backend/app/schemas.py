from datetime import date as DateType

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    is_admin: bool


class AuthStateResponse(BaseModel):
    authenticated: bool
    setup_required: bool
    user: UserResponse | None = None


class DashboardSummary(BaseModel):
    income: str = "0.00"
    recurring_bills: str = "0.00"
    planned_spending: str = "0.00"
    projected_balance: str = "0.00"
    available_cash: str = "0.00"
    net_position: str = "0.00"
    assets: str = "0.00"
    liabilities: str = "0.00"
    account_count: int = 0
    overdue_amount: str = "0.00"
    incomplete_recurring_count: int = 0
    bills_due_count: int = 0
    currency: str = "AUD"
    range_days: int = 90


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    recent_transactions: list[dict] = []
    upcoming: list[dict] = []
    top_planned_spending: list[dict] = []
    quick_stats: list[dict] = []
    empty_state: str


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    account_type: str
    institution: str | None = Field(default=None, max_length=120)
    opening_balance: str = "0.00"
    description: str | None = None
    account_suffix: str | None = Field(default=None, max_length=12)
    icon: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=24)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    account_type: str | None = None
    institution: str | None = Field(default=None, max_length=120)
    opening_balance: str | None = None
    description: str | None = None
    account_suffix: str | None = Field(default=None, max_length=12)
    icon: str | None = Field(default=None, max_length=80)
    color: str | None = Field(default=None, max_length=24)


class TransactionCreate(BaseModel):
    account_id: int
    date: DateType
    amount: str
    transaction_type: str
    description: str = Field(min_length=1, max_length=180)
    merchant: str | None = Field(default=None, max_length=180)
    category: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    source: str = "manual"
    status: str = "cleared"
    raw_description: str | None = None


class TransactionUpdate(BaseModel):
    account_id: int | None = None
    date: DateType | None = None
    amount: str | None = None
    transaction_type: str | None = None
    description: str | None = Field(default=None, min_length=1, max_length=180)
    merchant: str | None = Field(default=None, max_length=180)
    category: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    source: str | None = None
    status: str | None = None
    raw_description: str | None = None


class TransferCreate(BaseModel):
    from_account_id: int
    to_account_id: int
    date: DateType
    amount: str
    description: str = Field(min_length=1, max_length=180)
    notes: str | None = None


class TransferUpdate(BaseModel):
    from_account_id: int | None = None
    to_account_id: int | None = None
    date: DateType | None = None
    amount: str | None = None
    description: str | None = Field(default=None, min_length=1, max_length=180)
    notes: str | None = None


class IncomeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    amount: str | None = None
    frequency: str | None = None
    interval_count: int | None = None
    next_payment_date: DateType | None = None
    destination_account_id: int | None = None
    payer: str | None = Field(default=None, max_length=140)
    category: str | None = Field(default=None, max_length=80)
    is_active: bool = True
    start_date: DateType | None = None
    end_date: DateType | None = None
    notes: str | None = None


class RecurringExpenseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    amount: str | None = None
    frequency: str | None = None
    interval_count: int | None = None
    next_due_date: DateType | None = None
    direct_debit: bool | None = None
    account_id: int | None = None
    source_account_text: str | None = Field(default=None, max_length=140)
    category: str | None = Field(default=None, max_length=80)
    expense_type: str | None = Field(default=None, max_length=80)
    owner_group: str | None = Field(default=None, max_length=80)
    is_active: bool = True
    variable_amount: bool = False
    aliases: str | None = None
    notes: str | None = None
    last_paid_date: DateType | None = None


class BillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    provider: str | None = Field(default=None, max_length=140)
    bill_type: str | None = Field(default=None, max_length=80)
    priority: str = "normal"
    amount: str | None = None
    due_date: DateType | None = None
    account_id: int | None = None
    paid_through_date: DateType | None = None
    recurring_expense_id: int | None = None
    notes: str | None = None
