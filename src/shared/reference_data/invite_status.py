from enum import Enum


class InviteStatus(Enum):
    PENDING = "pending"
    SENT = "sent"
    USED = "used"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
