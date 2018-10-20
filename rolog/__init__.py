import sys
import asyncio
import warnings
import traceback
from datetime import datetime
from abc import ABC, abstractmethod
from enum import IntEnum
from collections import OrderedDict
from typing import Optional, List
from asyncio import Queue, QueueEmpty


class LogLevel(IntEnum):
    NONE = 0
    DEBUG = 10
    INFORMATION = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogRecord:

    __slots__ = ('time',
                 'logger_name',
                 'level',
                 'message',
                 'args',
                 'data')

    def __init__(self, _logger_name, _logger_level, message, *args, **kwargs):
        self.time = datetime.utcnow()
        self.logger_name = _logger_name
        self.level = _logger_level  # type: LogLevel
        self.message = message
        self.args = args
        self.data = kwargs


class ExceptionLogRecord(LogRecord):

    __slots__ = ('time',
                 'logger_name',
                 'level',
                 'message',
                 'args',
                 'data',
                 'exception')

    def __init__(self, _logger_name, _logger_level, message, exception, *args, **kwargs):
        super().__init__(_logger_name, _logger_level, message, *args, **kwargs)
        self.exception = exception


class LogTarget(ABC):
    """Base class for logs targets: targets send the log records
    (created by loggers) to the appropriate destination."""

    @abstractmethod
    async def log(self, record: LogRecord):
        pass


class FlushLogTarget(LogTarget, ABC):
    """Base class for flushing log targets: targets that send the log records
    (created by loggers) to the appropriate destination in groups."""

    def __init__(self,
                 queue: Optional[Queue]=None,
                 max_size: int=500,
                 fallback_target: Optional[LogTarget]=None,
                 max_retries: int=3,
                 retry_delay: float=0.6,
                 progressive_delay: bool=True):

        if queue is None:
            queue = Queue()

        if max_size < 1:
            raise ValueError('max_size must be positive and greater than 1')

        if retry_delay < 0:
            raise ValueError('retry_delay must be a positive number, to disable delays use max_retries parameter')

        self._queue = queue
        self._max_length = max_size
        self._fallback_target = fallback_target
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._progressive_delay = progressive_delay

    def get_delay(self, attempt):
        if self._progressive_delay:
            return self._retry_delay * attempt
        return self._retry_delay

    async def log(self, record: LogRecord):
        if not record:
            return
        await self._queue.put(record)

        if self.should_flush():
            await self.flush()

    @abstractmethod
    async def log_records(self, records: List[LogRecord]):
        pass

    async def log_records_with_retries(self, records: List[LogRecord], attempt: int):
        try:
            await self.log_records(records)
        except Exception as logging_ex:
            if attempt <= self._max_retries:
                delay = self.get_delay(attempt)

                details = traceback.format_exception(type(logging_ex), logging_ex, logging_ex.__traceback__)
                formatted_details = ''.join(details)

                warnings.warn(f'Failed to log records for {self.__class__.__name__}. '
                              f'Exception: {str(logging_ex)}'
                              f'Details: {formatted_details}'
                              f'Trying again in {delay} seconds; failed attempt n. {attempt}', RuntimeWarning)

                await asyncio.sleep(delay)

                await self.log_records_with_retries(records, attempt + 1)
            else:
                await self._try_using_fallback_target(records)

    async def _try_using_fallback_target(self, records: List[LogRecord]):
        fallback = self._fallback_target
        if not fallback:
            # log records are lost..
            warnings.warn(f'Failed to log records for {self.__class__.__name__}. '
                          f'Logging failed for configured retried: {self._max_retries}; '
                          f'A fallback target is not configured, hence log records are lost', RuntimeWarning)
            return

        warnings.warn(f'Failed to log records for {self.__class__.__name__}. '
                      f'Logging failed for configured retried: {self._max_retries}; '
                      f'A fallback target is not configured, hence log records are lost', RuntimeWarning)

        if isinstance(fallback, FlushLogTarget):
            await fallback.log_records(records)
        else:
            # assume it implements log_record method
            for record in records:
                await fallback.log(record)

    def _get(self):
        try:
            return self._queue.get_nowait()
        except QueueEmpty:
            return None

    def should_flush(self):
        return self._max_length <= self._queue.qsize()

    async def flush(self):
        data = []
        while True:
            item = self._get()
            if not item:
                break
            data.append(item)

        if data:
            await self.log_records_with_retries(data, 1)


class Logger:

    __slots__ = ('name',
                 '_targets',
                 'min_log_level',
                 'max_log_level')

    def __init__(self,
                 name,
                 targets,
                 min_log_level: LogLevel,
                 max_log_level: LogLevel):
        self.name = name
        self._targets = targets
        self.min_log_level = min_log_level
        self.max_log_level = max_log_level

    def get_exception(self, exception):
        if isinstance(exception, BaseException):
            return exception
        if not isinstance(exception, tuple):
            exception_type, exception, traceback = sys.exc_info()
            return exception

    def create_exception_record(self, message, level, *args, **kwargs):
        exception = kwargs.get('exception')
        if exception:
            exception = self.get_exception(exception)
            del kwargs['exception']
            return ExceptionLogRecord(self.name, level, message, exception, *args, **kwargs)

    def create_record(self, message, level, *args, **kwargs):
        if 'exception' in kwargs:
            return self.create_exception_record(message, level, *args, **kwargs)

        return LogRecord(self.name, level, message, *args, **kwargs)

    async def debug(self, message, *args, **kwargs):
        await self.log(message, LogLevel.DEBUG, *args, **kwargs)

    async def info(self, message, *args, **kwargs):
        await self.log(message, LogLevel.INFORMATION, *args, **kwargs)

    async def warning(self, message, *args, **kwargs):
        await self.log(message, LogLevel.WARNING, *args, **kwargs)

    async def error(self, message, *args, **kwargs):
        await self.log(message, LogLevel.ERROR, *args, **kwargs)

    async def exception(self, message, exception=True, *args, **kwargs):
        await self.log(message, LogLevel.ERROR, *args, exception=exception, **kwargs)

    async def critical(self, message, *args, **kwargs):
        await self.log(message, LogLevel.CRITICAL, *args, **kwargs)

    async def log(self, message, level: LogLevel=LogLevel.INFORMATION, *args, **kwargs):
        if level > self.max_log_level:
            return

        record = self.create_record(message, level, *args, **kwargs)
        current_level = level
        while current_level >= self.min_log_level:
            targets = self._targets[current_level]

            for target in targets:
                await target.log(record)

            current_level -= 10


class LoggerFactory:

    __slots__ = ('_targets',
                 '_instances',
                 'min_log_level',
                 'max_log_level',
                 'on_dispose_error')

    def __init__(self):
        self._targets = OrderedDict([(x, []) for x in list(LogLevel)])
        self._instances = {}
        self.min_log_level = LogLevel.DEBUG if __debug__ else LogLevel.INFORMATION
        self.max_log_level = LogLevel(max(LogLevel))
        self.on_dispose_error = None

    @property
    def targets(self):
        return self._targets

    def add_target(self,
                   target: LogTarget,
                   minimum_level: LogLevel=LogLevel.INFORMATION):
        try:
            self._targets[minimum_level].append(target)
        except KeyError:
            raise ValueError(f'Invalid minimum_level: {minimum_level}')

        return self

    def get_logger(self, name: str) -> Logger:
        try:
            return self._instances[name]
        except KeyError:
            logger = Logger(name,
                            self._targets,
                            self.min_log_level,
                            self.max_log_level)
            self._instances[name] = logger
            return logger

    async def dispose(self):
        # when a LoggerFactory is disposed, it's necessary to
        # flush all targets that implement flushing of messages,
        # to not lose logs, for example when the application is closed
        for level, target in self._targets.items():
            if isinstance(target, FlushLogTarget):
                try:
                    await target.flush()
                except Exception as ex:
                    # do not rethrow exception because other targets may require flushing;
                    if self.on_dispose_error:
                        self.on_dispose_error(ex)
