import os
import uuid
import pytest
from rolog import LogLevel, LoggerFactory, LogRecord
from rolog.targets import BuiltInLoggingTarget, DynamicBuiltInLoggingTarget
import logging
from rolog.tests import InMemoryTarget


def test_logger_factory_logger_name():
    factory = LoggerFactory()
    logger = factory.get_logger(__name__)

    assert __name__ == logger.name


def test_logger_factory_logger_same_instance_by_name():
    factory = LoggerFactory()
    logger_1 = factory.get_logger(__name__)
    logger_2 = factory.get_logger(__name__)

    assert logger_1 is not None
    assert logger_2 is not None
    assert logger_1 is logger_2

    logger_3 = factory.get_logger('foo')

    assert logger_3 is not None
    assert logger_3 is not logger_1


@pytest.mark.asyncio
async def test_records_have_timestamp():
    factory = LoggerFactory()
    test_target = InMemoryTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    for i in range(10):
        await logger.info(f'Hello, World {i}')

    for record in test_target.records:
        assert record.time


@pytest.mark.asyncio
async def test_records_support_extra_arguments():
    factory = LoggerFactory()
    test_target = InMemoryTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    await logger.info('Hello, World', 'One', 'Two', 'Three')

    record = test_target.records[0]  # type: LogRecord
    assert ('One', 'Two', 'Three') == record.args


@pytest.mark.asyncio
async def test_records_support_extra_data():
    factory = LoggerFactory()
    test_target = InMemoryTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    await logger.info('Hello, World', id=2016, name='Tyberiusz')

    record = test_target.records[0]  # type: LogRecord
    assert {
        'id': 2016,
        'name': 'Tyberiusz'
    } == record.data


@pytest.mark.asyncio
async def test_records_support_extra_data_and_args():
    factory = LoggerFactory()
    test_target = InMemoryTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    assert logger is not None

    await logger.info('Hello, World', 100, 200, id=2016, name='Tyberiusz')

    record = test_target.records[0]  # type: LogRecord
    assert (100, 200) == record.args
    assert {
        'id': 2016,
        'name': 'Tyberiusz'
    } == record.data


@pytest.mark.asyncio
async def test_logger_factory_two_targets():
    factory = LoggerFactory()
    test_target_1 = InMemoryTarget()
    test_target_2 = InMemoryTarget()

    factory\
        .add_target(test_target_1) \
        .add_target(test_target_2)

    logger = factory.get_logger(__name__)

    assert logger is not None
    await logger.log('Hello, World')

    assert 'Hello, World' == test_target_1.records[0].message
    assert 'Hello, World' == test_target_2.records[0].message


@pytest.mark.asyncio
async def test_logger_factory_minimum_level():
    factory = LoggerFactory()
    test_target_1 = InMemoryTarget()
    test_target_2 = InMemoryTarget()

    factory\
        .add_target(test_target_1, LogLevel.INFORMATION) \
        .add_target(test_target_2, LogLevel.ERROR)

    logger = factory.get_logger(__name__)
    assert logger is not None
    await logger.info('Hello, World')

    assert 'Hello, World' == test_target_1.records[0].message
    assert not test_target_2.records

    await logger.error('Oh, no!')

    assert 'Oh, no!' == test_target_1.records[1].message
    assert 'Oh, no!' == test_target_2.records[0].message


@pytest.mark.asyncio
async def test_logger_factory_minimum_level_to_debug():
    factory = LoggerFactory()

    test_target_1 = InMemoryTarget()
    test_target_2 = InMemoryTarget()
    test_target_3 = InMemoryTarget()

    factory \
        .add_target(test_target_1, LogLevel.DEBUG) \
        .add_target(test_target_2, LogLevel.INFORMATION) \
        .add_target(test_target_3, LogLevel.ERROR)

    logger = factory.get_logger(__name__)

    assert logger is not None

    await logger.info('Hello, World')

    assert 'Hello, World' == test_target_1.records[0].message
    assert 'Hello, World' == test_target_2.records[0].message
    assert not test_target_3.records

    await logger.debug('Lorem ipsum')

    assert 2 == len(test_target_1.records)
    assert 'Lorem ipsum' == test_target_1.records[1].message
    assert 1 == len(test_target_2.records)
    assert not test_target_3.records


@pytest.mark.asyncio
async def test_logger_exception():
    factory = LoggerFactory()
    test_target = InMemoryTarget()
    factory.add_target(test_target)
    logger = factory.get_logger(__name__)

    try:
        1 / 0
    except Exception as ex:
        # passing exception
        await logger.exception('Oh, no!', ex)

    assert 'Oh, no!' == test_target.records[0].message

    try:
        1 / 0
    except Exception:
        # without passing exception
        await logger.exception('Oh, no2!')

    assert 'Oh, no2!' == test_target.records[1].message


def get_builtin_sync_logger(name):
    sync_logger = logging.getLogger(name)
    sync_logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(name + '.log')
    fh.setLevel(logging.DEBUG)
    sync_logger.addHandler(fh)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    return sync_logger


@pytest.mark.asyncio
async def test_logger_wrapping_sync_logging():
    name = str(uuid.uuid4())
    sync_logger = get_builtin_sync_logger(name)

    factory = LoggerFactory()
    factory.add_target(BuiltInLoggingTarget(sync_logger))
    logger = factory.get_logger(name)

    await logger.info('Lorem ipsum dolor sit amet')

    try:
        1 / 0
    except Exception as ex:
        # passing exception
        await logger.exception('Oh, no!')

    with open(name + '.log', mode='rt', encoding='utf8') as file_log:
        content = file_log.read()

        assert 'Lorem ipsum dolor sit amet' in content
        assert 'ZeroDivisionError: division by zero' in content

    os.remove(name + '.log')


@pytest.mark.asyncio
async def test_logger_wrapping_sync_logging_dynamic_target():
    name = str(uuid.uuid4())
    get_builtin_sync_logger(name)

    factory = LoggerFactory()
    factory.add_target(DynamicBuiltInLoggingTarget())
    logger = factory.get_logger(name)

    await logger.info('Lorem ipsum dolor sit amet')

    try:
        1 / 0
    except Exception as ex:
        # passing exception
        await logger.exception('Oh, no!')

    with open(name + '.log', mode='rt', encoding='utf8') as file_log:
        content = file_log.read()

        assert 'Lorem ipsum dolor sit amet' in content
        assert 'ZeroDivisionError: division by zero' in content

    os.remove(name + '.log')
