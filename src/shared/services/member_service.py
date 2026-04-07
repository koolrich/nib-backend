import json

from aws_lambda_powertools import Logger

logger = Logger()


def get_my_pledges(uow, member_id: str) -> dict:
    rows = uow.pledges.get_by_member(member_id)
    pledges = []
    for row in rows:
        r = dict(row)
        contribution = None
        if r.get("contribution_amount") is not None:
            contribution = {
                "amount": r["contribution_amount"],
                "received_at": r["contribution_received_at"],
            }
        r.pop("contribution_amount", None)
        r.pop("contribution_received_at", None)
        r["contribution"] = contribution
        pledges.append(r)
    return {"statusCode": 200, "body": json.dumps({"pledges": pledges}, default=str)}


def patch_member(uow, caller: dict, target_member_id: str, body: dict) -> dict:
    caller_id = str(caller["id"])
    caller_role = caller["member_role"]
    is_privileged = caller_role in ("executive", "admin")

    if caller_id != target_member_id and not is_privileged:
        return {"statusCode": 403, "body": json.dumps({"error": "You can only update your own profile"})}

    target = uow.members.get_by_id(target_member_id)
    if not target:
        return {"statusCode": 404, "body": json.dumps({"error": "Member not found"})}

    restricted = {"member_role", "status"}
    if any(k in body for k in restricted) and not is_privileged:
        return {"statusCode": 403, "body": json.dumps({"error": "Only executives and admins can update role or status"})}

    row = uow.members.update(target_member_id, body)
    return {"statusCode": 200, "body": json.dumps(dict(row), default=str)}
