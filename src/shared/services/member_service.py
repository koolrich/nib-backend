import json

from aws_lambda_powertools import Logger
from shared.serializers.member_serializers import serialize_member, serialize_member_pledge, serialize_member_list_item

logger = Logger()


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def get_my_profile(uow, member_id: str) -> dict:
    member = uow.members.get_by_id(member_id)
    if not member:
        return _response(404, {"error": "Member not found"})
    return _response(200, serialize_member(member))


def get_my_pledges(uow, member_id: str) -> dict:
    rows = uow.pledges.get_by_member(member_id)
    return _response(200, {"pledges": [serialize_member_pledge(r) for r in rows]})


def get_member_profile(uow, member_id: str) -> dict:
    member = uow.members.get_by_id(member_id)
    if not member:
        return _response(404, {"error": "Member not found"})
    return _response(200, serialize_member(member))


def list_members(uow, caller: dict, search: str | None = None) -> dict:
    is_exec = caller["member_role"] in ("executive", "admin")
    rows = uow.members.get_all(search=search)
    return _response(200, {"members": [serialize_member_list_item(r, is_exec=is_exec) for r in rows]})


def patch_member(uow, caller: dict, target_member_id: str, body: dict) -> dict:
    caller_id = str(caller["id"])
    caller_role = caller["member_role"]
    is_privileged = caller_role in ("executive", "admin")

    if caller_id != target_member_id and not is_privileged:
        return _response(403, {"error": "You can only update your own profile"})

    target = uow.members.get_by_id(target_member_id)
    if not target:
        return _response(404, {"error": "Member not found"})

    restricted = {"member_role", "status"}
    if any(k in body for k in restricted) and not is_privileged:
        return _response(403, {"error": "Only executives and admins can update role or status"})

    row = uow.members.update(target_member_id, body)
    return _response(200, serialize_member(row))
