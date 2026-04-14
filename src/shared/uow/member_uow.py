from shared.uow.base import UnitOfWork
from shared.repositories.member_repository import MemberRepository
from shared.repositories.organisation_repository import OrganisationRepository
from shared.repositories.pledge_repository import PledgeRepository


class MemberUoW(UnitOfWork):
    def __enter__(self):
        super().__enter__()
        self.members = MemberRepository(self.conn)
        self.organisation = OrganisationRepository(self.conn)
        self.pledges = PledgeRepository(self.conn)
        return self
