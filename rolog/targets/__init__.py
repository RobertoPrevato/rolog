import logging
from rolog import LogTarget, LogRecord, ExceptionLogRecord


class BuiltInLoggingTarget(LogTarget):
    """rolog target for loggers from built-in logging module"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def log(self, record: LogRecord):
        if isinstance(record, ExceptionLogRecord):
            self.logger.exception(record.message,
                                  *record.args,
                                  exc_info=record.exception,
                                  **record.data)
            return

        self.logger.log(record.level.value,
                        record.message,
                        *record.args,
                        **record.data)


class DynamicBuiltInLoggingTarget(LogTarget):
    """rolog target for loggers from built-in logging module, obtained dynamically by record logger names"""

    def __init__(self):
        self._instances = {}

    def get_sync_logger(self, name):
        try:
            return self._instances[name]
        except KeyError:
            sync_logger = BuiltInLoggingTarget(logging.getLogger(name))
            self._instances[name] = sync_logger
            return sync_logger

    async def log(self, record: LogRecord):
        sync_logger = self.get_sync_logger(record.logger_name)
        await sync_logger.log(record)
