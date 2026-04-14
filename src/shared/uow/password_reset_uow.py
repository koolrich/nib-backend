from shared.uow.base import UnitOfWork
from shared.repositories.member_repository import MemberRepository
from shared.repositories.password_reset_repository import PasswordResetRepository


class PasswordResetUoW(UnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.members = MemberRepository(self.conn)
        self.password_reset = PasswordResetRepository(self.conn)
        return self
