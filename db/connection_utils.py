import asyncpg


class Connector:
    def __init__(self):
        self.pool: None | asyncpg.Pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(database="postgres", user="postgres", port=5431, host="127.0.0.1")

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
