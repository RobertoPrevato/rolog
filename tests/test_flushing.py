import pytest
import asyncio
from typing import List
from pytest import raises
from rolog import LoggerFactory, FlushLogTarget, LogRecord, LogLevel, LogTarget
from tests import InMemoryTarget


class CrashTest(Exception):

    def __init__(self):
        super().__init__('Crash Test!')


class InMemoryFlushLogTarget(FlushLogTarget):

    def __init__(self, max_size=20, *args, **kwargs):
        super().__init__(max_size=max_size, *args, **kwargs)
        self.destination = []

    async def log_records(self, records: List[LogRecord]):
        for record in records:
            self.destination.append(record)


class FailingFlushLogTarget(FlushLogTarget):

    def __init__(self, max_size, fallback_target=None):
        if fallback_target is None:
            fallback_target = InMemoryTarget()

        self.fallback = fallback_target
        super().__init__(max_size=max_size,
                         fallback_target=self.fallback,
                         retry_delay=0.001,
                         progressive_delay=False)

    async def log_records(self, records: List[LogRecord]):
        await asyncio.sleep(0.001)
        raise CrashTest()


class FailingLogTarget(LogTarget):

    async def log(self, record: LogRecord):
        raise CrashTest()


class FailingFlushLogTargetNoFallback(FlushLogTarget):

    def __init__(self, max_size):
        super().__init__(max_size=max_size,
                         max_retries=3,
                         fallback_target=None,
                         retry_delay=0.001,
                         progressive_delay=False)

    async def log_records(self, records: List[LogRecord]):
        await asyncio.sleep(0.001)
        raise CrashTest()


class FailingFlushLogTargetFailFallback(FlushLogTarget):

    def __init__(self, max_size):
        super().__init__(max_size=max_size,
                         max_retries=3,
                         fallback_target=FailingLogTarget(),
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
@pytest.mark.parametrize('log_level', [level for level in LogLevel if level != LogLevel.NONE])
async def test_log_message_type_shortcuts(log_level):
    max_size = 5

    factory = LoggerFactory()
    factory.min_log_level = LogLevel.NONE
    test_target = InMemoryFlushLogTarget(max_size)
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(max_size):
        if log_level == LogLevel.DEBUG:
            await logger.debug(f'Message: {i}')

        if log_level == LogLevel.INFORMATION:
            await logger.info(f'Message: {i}')

        if log_level == LogLevel.CRITICAL:
            await logger.critical(f'Message: {i}')

        if log_level == LogLevel.ERROR:
            await logger.error(f'Message: {i}')

        if log_level == LogLevel.WARNING:
            await logger.warning(f'Message: {i}')

    # all records must be present in destinations
    assert len(test_target.destination) == max_size

    i = 0
    for record in test_target.destination:
        assert f'Message: {i}' == record.message
        assert record.level == log_level
        i += 1


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
async def test_logger_throws_for_too_high_log_level():
    factory = LoggerFactory()
    factory.min_log_level = LogLevel.NONE
    test_target = InMemoryFlushLogTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    with raises(ValueError, match='Invalid log level'):
        await logger.log('Something', level=max(LogLevel) + 1)


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


@pytest.mark.parametrize('invalid_value', [0, -1, -100])
def test_flush_target_throws_for_invalid_max_size(invalid_value):

    with raises(ValueError, match='max_size must be positive and greater than 1'):
        InMemoryFlushLogTarget(max_size=invalid_value)


@pytest.mark.parametrize('invalid_value', [-1, -100])
def test_flush_target_throws_for_invalid_retry_delay(invalid_value):

    with raises(ValueError, match='retry_delay must be a positive number, to disable delays use max_retries parameter'):
        InMemoryFlushLogTarget(retry_delay=invalid_value)


@pytest.mark.parametrize('retry_delay,attempt,expected_value', [
    [1, 1, 1],
    [2, 1, 2],
    [1, 2, 2],
    [1, 3, 3],
    [5, 3, 15],
    [10, 3, 30]
])
def test_flush_target_progressive_delay(retry_delay, attempt, expected_value):
    target = InMemoryFlushLogTarget(retry_delay=retry_delay)

    assert target.get_delay(attempt) == expected_value


@pytest.mark.asyncio
async def test_flush_target_ignores_null_record():
    target = InMemoryFlushLogTarget(max_size=5)

    for i in range(10):
        await target.log(None)

    assert target.should_flush() is False


@pytest.mark.asyncio
async def test_logger_factory_flushes_when_disposing():
    factory = LoggerFactory()
    target_1 = InMemoryFlushLogTarget(5)
    target_2 = InMemoryFlushLogTarget(5)

    factory.add_target(target_1)
    factory.add_target(target_2)

    logger = factory.get_logger('example')

    for i in range(3):
        await logger.info(f'Hello, World {i}')

    assert len(target_1.destination) == 0
    assert len(target_2.destination) == 0

    await factory.dispose()

    assert len(target_1.destination) == 3
    assert len(target_2.destination) == 3


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
async def test_logger_factory_flushes_when_disposing_handling_exceptions():
    factory = LoggerFactory()
    target_1 = FailingFlushLogTarget(5)
    target_2 = InMemoryFlushLogTarget(5)

    factory.add_target(target_1)
    factory.add_target(target_2)

    logger = factory.get_logger('example')

    for i in range(3):
        await logger.info(f'Hello, World {i}')

    assert len(target_2.destination) == 0

    await factory.dispose()

    assert len(target_2.destination) == 3


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
async def test_logger_factory_on_dispose_error_callback():
    factory = LoggerFactory()
    factory.add_target(FailingFlushLogTargetFailFallback(5))

    k = 0

    def on_error_callback(exc):
        nonlocal k
        k = 1
        assert isinstance(exc, CrashTest)

    factory.on_dispose_error = on_error_callback

    logger = factory.get_logger('example')

    for i in range(3):
        await logger.info(f'Hello, World {i}')

    await factory.dispose()

    assert k == 1


@pytest.mark.asyncio
async def test_flush_target_no_fallback_warning_with_graceful_handling():
    factory = LoggerFactory()
    max_size = 2
    test_target = FailingFlushLogTargetNoFallback(max_size)
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(max_size - 1):
        await logger.info(f'Message: {i}')

    with pytest.warns(RuntimeWarning, match='Failed to log records for'):
        await logger.info(f'Message: {max_size - 1}')


@pytest.mark.asyncio
@pytest.mark.filterwarnings('ignore::RuntimeWarning')
async def test_flushing_fallback_nested_flushing_target():
    factory = LoggerFactory()
    max_size = 5
    test_target = FailingFlushLogTarget(max_size, fallback_target=InMemoryFlushLogTarget(max_size=max_size))
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(max_size - 1):
        await logger.info(f'Message: {i}')

    await logger.info(f'Message: {max_size - 1}')

    assert max_size == len(test_target.fallback.destination)

    i = 0
    for record in test_target.fallback.destination:
        assert f'Message: {i}' == record.message
        i += 1
