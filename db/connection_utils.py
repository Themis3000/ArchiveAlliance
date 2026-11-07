import asyncpg
import os


class Connector:
    def __init__(self):
        self.pool: None | asyncpg.Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(database=os.environ["DB"],
                                              user=os.environ["USER"],
                                              password=os.environ["PASSWORD"],
                                              port=os.environ["PORT"],
                                              host=os.environ["HOST"])

    def get_conn(self):
        if self.pool is None:
            raise NoPoolOpen()
        return self.pool.acquire()

    async def disconnect(self):
        if self.pool is None:
            raise NoPoolOpen()
        await self.pool.close()


class NoPoolOpen(Exception):
    pass
