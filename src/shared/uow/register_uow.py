from shared.uow.base import UnitOfWork
from shared.repositories.member_repository import MemberRepository
from shared.repositories.invite_repository import InviteRepository
from shared.repositories.membership_repository import MembershipRepository
from shared.repositories.membership_period_repository import MembershipPeriodRepository
from shared.repositories.invoice_repository import InvoiceRepository


class RegisterUoW(UnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.members = MemberRepository(self.conn)
        self.invites = InviteRepository(self.conn)
        self.memberships = MembershipRepository(self.conn)
        self.periods = MembershipPeriodRepository(self.conn)
        self.invoices = InvoiceRepository(self.conn)
        return self
