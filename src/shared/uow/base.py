from shared.db import get_connection


class UnitOfWork:
    def __enter__(self):
        self.conn = get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        return False
