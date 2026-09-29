import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from allergen_kg.fixtures import add_edges
from allergen_kg.graph import get_allergen_closure


@unittest.skipUnless(os.getenv("RUN_PG_TESTS") == "1", "set RUN_PG_TESTS=1 with docker Postgres running")
class PostgresClosureTests(unittest.TestCase):
    def setUp(self):
        from database.db import DATABASE_URL
        self.engine = create_engine(DATABASE_URL)
        self.conn = self.engine.connect()
        self.trans = self.conn.begin()
        self.db = Session(bind=self.conn, join_transaction_mode="create_savepoint")

    def tearDown(self):
        self.db.close()
        self.trans.rollback()
        self.conn.close()
        self.engine.dispose()

    def test_recursive_cte_runs_on_postgres(self):
        add_edges(self.db, [
            ("zz_pg_alpha", "allergen:zz_pg_key"),
            ("zz_pg_beta", "zz_pg_alpha"),
            ("zz_pg_gamma", "zz_pg_beta"),
            ("zz_pg_alpha", "zz_pg_gamma"),
        ])
        closure = {e.name: e.path for e in get_allergen_closure(self.db, "zz_pg_key")}
        self.assertEqual(closure["zz_pg_gamma"], ("zz_pg_gamma", "zz_pg_beta", "zz_pg_alpha"))
        self.assertEqual(set(closure), {"zz_pg_alpha", "zz_pg_beta", "zz_pg_gamma"})


if __name__ == "__main__":
    unittest.main()
