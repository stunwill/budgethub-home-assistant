from fastapi import APIRouter

from . import v12_mount
from .banking import (
    connect_mock,
    disconnect,
    link_external_account,
    list_connections,
    providers,
    sync_history,
    sync_now,
)

router = APIRouter()
bank_router = APIRouter(prefix="/bank-connections")
bank_router.add_api_route("/providers", providers, methods=["GET"])
bank_router.add_api_route("", list_connections, methods=["GET"])
bank_router.add_api_route("/mock/connect", connect_mock, methods=["POST"], status_code=201)
bank_router.add_api_route("/{connection_id}/accounts/{external_account_id}/link", link_external_account, methods=["POST"])
bank_router.add_api_route("/{connection_id}/sync", sync_now, methods=["POST"])
bank_router.add_api_route("/{connection_id}/disconnect", disconnect, methods=["POST"])
bank_router.add_api_route("/{connection_id}/sync-history", sync_history, methods=["GET"])

router.include_router(bank_router)
router.include_router(v12_mount.router)
