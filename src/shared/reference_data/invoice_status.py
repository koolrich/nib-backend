from enum import Enum


class InvoiceStatus(Enum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
