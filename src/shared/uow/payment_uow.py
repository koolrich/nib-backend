from shared.uow.base import UnitOfWork
from shared.repositories.member_repository import MemberRepository
from shared.repositories.membership_period_repository import MembershipPeriodRepository
from shared.repositories.invoice_repository import InvoiceRepository
from shared.repositories.payment_repository import PaymentRepository


class PaymentUoW(UnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.members = MemberRepository(self.conn)
        self.periods = MembershipPeriodRepository(self.conn)
        self.invoices = InvoiceRepository(self.conn)
        self.payments = PaymentRepository(self.conn)
        return self
