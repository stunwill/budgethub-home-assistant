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
    income: float = 0
    recurring_bills: float = 0
    planned_spending: float = 0
    projected_balance: float = 0
    currency: str = "AUD"
    range_days: int = 90


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    upcoming: list[dict] = []
    top_planned_spending: list[dict] = []
    quick_stats: list[dict] = []
    empty_state: str
