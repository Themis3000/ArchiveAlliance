import asyncpg
import os
from .sqlc import queries


class Connector:
    def __init__(self):
        self.pool: None | asyncpg.Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(database=os.environ["DB"],
                                              user=os.environ["USER"],
                                              password=os.environ["PASSWORD"],
                                              port=os.environ["PORT"],
                                              host=os.environ["HOST"])
        async with self.get_conn() as conn:
            tables = await queries.get_table_count(conn)
        if tables == 0:
            await self.init_db()

    def get_conn(self):
        if self.pool is None:
            raise NoPoolOpen()
        return self.pool.acquire()

    async def disconnect(self):
        if self.pool is None:
            raise NoPoolOpen()
        await self.pool.close()

    async def init_db(self):
        async with self.get_conn() as conn:
            with open("./db/sqlc/schema.sql", "r") as f:
                await conn.execute(f.read())


class NoPoolOpen(Exception):
    pass
