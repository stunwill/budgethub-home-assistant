from fastapi import APIRouter

from . import v12_household
from .banking import (
    connect_mock,
    disconnect,
    link_external_account,
    list_connections,
    providers,
    sync_history,
    sync_now,
)

router = APIRouter(prefix="/bank-connections")
router.add_api_route("/providers", providers, methods=["GET"])
router.add_api_route("", list_connections, methods=["GET"])
router.add_api_route("/mock/connect", connect_mock, methods=["POST"], status_code=201)
router.add_api_route("/{connection_id}/accounts/{external_account_id}/link", link_external_account, methods=["POST"])
router.add_api_route("/{connection_id}/sync", sync_now, methods=["POST"])
router.add_api_route("/{connection_id}/disconnect", disconnect, methods=["POST"])
router.add_api_route("/{connection_id}/sync-history", sync_history, methods=["GET"])

# v1.2 Household Identity & Access is intentionally layered onto the existing
# v1.0/v1.1 router stack rather than replacing banking or financial services.
# Importing v12_household also extends the startup migration chain to schema 12.
router.include_router(v12_household.router)
