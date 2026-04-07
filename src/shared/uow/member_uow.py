from shared.uow.base import UnitOfWork
from shared.repositories.member_repository import MemberRepository
from shared.repositories.pledge_repository import PledgeRepository


class MemberUoW(UnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.members = MemberRepository(self.conn)
        self.pledges = PledgeRepository(self.conn)
        return self
