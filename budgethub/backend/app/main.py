from fastapi import FastAPI

APP_VERSION = "0.1.0"

app = FastAPI(
    title="BudgetHub API",
    version=APP_VERSION,
    description="BudgetHub household budgeting and cash-flow forecasting API.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "BudgetHub", "version": APP_VERSION}


@app.get("/api/version")
def version() -> dict[str, str]:
    return {"version": APP_VERSION}
