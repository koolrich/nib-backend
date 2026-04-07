import json

from aws_lambda_powertools import Logger
from shared.services.cognito_service import sign_up, confirm_sign_up, delete_user

logger = Logger()


def register(uow, request) -> dict:
    invite = uow.invites.get_by_activation_code(request.activation_code)
    if not invite:
        return {"statusCode": 404, "body": json.dumps({"error": "Invalid activation code"})}

    if invite["relationship"] == "other" and not request.membership_type:
        return {"statusCode": 400, "body": json.dumps({"error": "membership_type is required"})}

    cognito_username = None
    try:
        cognito_username, cognito_sub = sign_up(request.mobile, request.password)
        confirm_sign_up(cognito_username)

        date_joined = invite["date_joined"] if invite["is_legacy"] and invite["date_joined"] else None
        member_id = uow.members.insert(request, cognito_sub, str(invite["invited_by"]), invite["is_legacy"], date_joined)

        if invite["relationship"] == "other":
            membership_id = uow.memberships.insert(request.membership_type, member_id)
            uow.memberships.update_member_membership_id(member_id, membership_id)
            period = uow.periods.insert(membership_id)
            uow.invoices.insert(str(period["id"]), request.membership_type)
        else:
            inviter_membership_id = uow.memberships.get_id_by_member_id(str(invite["invited_by"]))
            if not inviter_membership_id:
                raise RuntimeError("Inviter has no membership to link spouse to")
            uow.memberships.update_member_membership_id(member_id, inviter_membership_id)

        uow.invites.mark_used(str(invite["id"]), member_id)
        return {"statusCode": 201, "body": json.dumps({"message": "Registration successful"})}

    except Exception:
        if cognito_username:
            try:
                delete_user(cognito_username)
                logger.info("Rolled back Cognito user")
            except Exception as ce:
                logger.exception("Failed to rollback Cognito user", extra={"error": str(ce)})
        raise
