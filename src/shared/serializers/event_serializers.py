def serialize_event_create(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "date": str(row["date"]),
        "type": row["type"],
        "status": row["status"],
        "description": row["description"],
        "created_at": str(row["created_at"]),
    }


def serialize_event(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "date": str(row["date"]),
        "type": row["type"],
        "status": row["status"],
        "description": row["description"],
        "created_at": str(row["created_at"]),
        "total_contributions": float(row["total_contributions"]),
        "total_pledges": int(row["total_pledges"]),
    }


def serialize_event_update(row) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "date": str(row["date"]),
        "type": row["type"],
        "status": row["status"],
        "description": row["description"],
        "updated_at": str(row["updated_at"]),
    }


def serialize_item(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "name": row["name"],
        "unit": row["unit"],
        "quantity_needed": float(row["quantity_needed"]),
        "quantity_pledged": float(row["quantity_pledged"]),
        "quantity_remaining": float(row["quantity_remaining"]),
        "is_available": row["is_available"],
    }


def serialize_item_insert(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "name": row["name"],
        "quantity_needed": float(row["quantity_needed"]),
        "unit": row["unit"],
        "created_at": str(row["created_at"]),
    }


def serialize_pledge(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "member_id": str(row["member_id"]),
        "member_name": row["member_name"],
        "event_item_id": str(row["event_item_id"]),
        "item_name": row["item_name"],
        "quantity": float(row["quantity"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
    }


def serialize_pledge_write(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "member_id": str(row["member_id"]),
        "event_item_id": str(row["event_item_id"]),
        "quantity": float(row["quantity"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
    }


def serialize_pledge_update(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "member_id": str(row["member_id"]),
        "event_item_id": str(row["event_item_id"]),
        "quantity": float(row["quantity"]),
        "status": row["status"],
        "updated_at": str(row["updated_at"]),
    }


def serialize_pledge_cancel(row) -> dict:
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "updated_at": str(row["updated_at"]),
    }


def serialize_contribution(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "member_id": str(row["member_id"]) if row["member_id"] else None,
        "member_name": row["member_name"],
        "pledge_id": str(row["pledge_id"]) if row["pledge_id"] else None,
        "amount": float(row["amount"]),
        "received_at": str(row["received_at"]),
        "note": row["note"],
    }


def serialize_contribution_insert(row) -> dict:
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "member_id": str(row["member_id"]) if row["member_id"] else None,
        "pledge_id": str(row["pledge_id"]) if row["pledge_id"] else None,
        "amount": float(row["amount"]),
        "received_at": str(row["received_at"]),
        "note": row["note"],
        "created_at": str(row["created_at"]),
    }
