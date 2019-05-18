import pytest
import asyncio
from typing import List
from rolog import LoggerFactory, FlushLogTarget, LogRecord
from tests import InMemoryTarget


class CrashTest(Exception):

    def __init__(self):
        super().__init__('Crash Test!')


class InMemoryFlushLogTarget(FlushLogTarget):

    def __init__(self, max_size=20):
        super().__init__(max_size=max_size)
        self.destination = []

    async def log_records(self, records: List[LogRecord]):
        for record in records:
            self.destination.append(record)


class FailingFlushLogTarget(FlushLogTarget):

    def __init__(self, max_size):
        self.fallback = InMemoryTarget()
        super().__init__(max_size=max_size,
                         fallback_target=self.fallback,
                         retry_delay=0.001,
                         progressive_delay=False)

    async def log_records(self, records: List[LogRecord]):
        await asyncio.sleep(0.001)
        raise CrashTest()


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
@pytest.mark.parametrize('max_size', [
    2, 10, 20, 30
])
async def test_flushing(max_size):
    factory = LoggerFactory()
    test_target = InMemoryFlushLogTarget(max_size)
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(max_size - 1):
        await logger.info(f'Message: {i}')

    assert 0 == len(test_target.destination)

    await logger.info(f'Message: {max_size - 1}')

    # now all records must be present in destinations
    assert max_size == len(test_target.destination)

    i = 0
    for record in test_target.destination:
        assert f'Message: {i}' == record.message
        i += 1


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
async def test_flushing_fallback_when_fails():
    factory = LoggerFactory()
    max_size = 2
    test_target = FailingFlushLogTarget(max_size)
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(max_size - 1):
        await logger.info(f'Message: {i}')

    await logger.info(f'Message: {max_size - 1}')

    # since we forced failure, records should be logged in fallback target
    assert max_size == len(test_target.fallback.records)

    i = 0
    for record in test_target.fallback.records:
        assert f'Message: {i}' == record.message
        i += 1
