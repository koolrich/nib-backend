def serialize_period(row) -> dict:
    return {
        "id": str(row["id"]),
        "membership_id": str(row["membership_id"]),
        "start_date": str(row["start_date"]),
        "end_date": str(row["end_date"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
    }


def serialize_invoice(row) -> dict:
    return {
        "id": str(row["id"]),
        "membership_period_id": str(row["membership_period_id"]),
        "invoice_number": row["invoice_number"],
        "issue_date": str(row["issue_date"]),
        "due_date": str(row["due_date"]),
        "amount_due": float(row["amount_due"]),
        "status": row["status"],
        "created_at": str(row["created_at"]),
    }
