def serialize_member(row) -> dict:
    return {
        "id": str(row["id"]),
        "first_name": row["first_name"],
        "last_name": row["last_name"],
        "email": row["email"],
        "mobile": row["mobile"],
        "address_line1": row["address_line1"],
        "address_line2": row["address_line2"],
        "town": row["town"],
        "post_code": row["post_code"],
        "state_of_origin": row["state_of_origin"],
        "lga": row["lga"],
        "birthday_day": row["birthday_day"],
        "birthday_month": row["birthday_month"],
        "relationship_status": row["relationship_status"],
        "emergency_contact_name": row["emergency_contact_name"],
        "emergency_contact_phone": row["emergency_contact_phone"],
        "member_role": row["member_role"],
        "status": row["status"],
    }


def serialize_member_pledge(row) -> dict:
    contribution = None
    if row["contribution_amount"] is not None:
        contribution = {
            "amount": float(row["contribution_amount"]),
            "received_at": str(row["contribution_received_at"]),
        }
    return {
        "id": str(row["id"]),
        "event_id": str(row["event_id"]),
        "event_title": row["event_title"],
        "event_date": str(row["event_date"]),
        "item_name": row["item_name"],
        "unit": row["unit"],
        "quantity": float(row["quantity"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
        "contribution": contribution,
    }
