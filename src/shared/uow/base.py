from shared.db import get_connection, _open_connection, preload_params


class UnitOfWork:
    def __enter__(self):
        self.conn = get_connection()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            try:
                self.conn.rollback()
            except Exception:
                pass
        else:
            try:
                self.conn.commit()
            except Exception:
                import shared.db as db
                db._connection = _open_connection(preload_params())
                raise
        return False
