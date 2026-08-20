from fastapi import APIRouter

from . import v12_household as household
from . import v12_extra as extra

router = APIRouter(prefix="/household", tags=["household"])
router.add_api_route("/current", household.current_household, methods=["GET"])
router.add_api_route("/current", household.update_household, methods=["PUT"])
router.add_api_route("/members", household.list_members, methods=["GET"])
router.add_api_route("/members", household.create_member, methods=["POST"], status_code=201)
router.add_api_route("/members/{user_id}", household.update_member, methods=["PUT"])
router.add_api_route("/members/{user_id}/deactivate", household.deactivate_member, methods=["POST"])
router.add_api_route("/members/{user_id}/reactivate", household.reactivate_member, methods=["POST"])
router.add_api_route("/members/{user_id}/password-reset", household.reset_member_password, methods=["POST"])
router.add_api_route("/members/{user_id}/mfa-reset", household.reset_member_mfa, methods=["POST"])
router.add_api_route("/members/{user_id}/sessions/revoke", household.revoke_member_sessions, methods=["POST"])
router.add_api_route("/ownership/accounts/{account_id}", household.account_ownership, methods=["GET"])
router.add_api_route("/ownership/accounts/{account_id}", household.update_account_ownership, methods=["PUT"])
router.add_api_route("/me/security", extra.my_household_security, methods=["GET"])
router.add_api_route("/me/change-temporary-password", household.change_temporary_password, methods=["POST"])
