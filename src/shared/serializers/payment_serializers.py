def serialize_payment(row) -> dict:
    return {
        "id": str(row["id"]),
        "invoice_id": str(row["invoice_id"]),
        "amount": float(row["amount"]),
        "method": row["method"],
        "reference": row["reference"],
        "received_at": str(row["received_at"]),
        "note": row["note"],
        "created_at": str(row["created_at"]),
    }


def serialize_statement_payment(row) -> dict:
    return {
        "id": str(row["id"]),
        "amount": float(row["amount"]),
        "method": row["method"],
        "reference": row["reference"],
        "received_at": str(row["received_at"]),
        "note": row["note"],
        "created_at": str(row["created_at"]),
    }
