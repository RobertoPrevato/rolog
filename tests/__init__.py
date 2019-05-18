from rolog import LogTarget


class InMemoryTarget(LogTarget):

    def __init__(self):
        self.records = []

    async def log(self, record):
        self.records.append(record)
