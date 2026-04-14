from shared.instrumentation.tracer import tracer


class OrganisationRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="OrganisationGet")
    def get(self) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT account_name, account_number, sort_code, bank_name FROM organisation LIMIT 1"
            )
            return cur.fetchone()
