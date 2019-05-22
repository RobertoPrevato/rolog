from rolog import LoggerFactory, Logger
from rodi import Container


def use_logging(self: Container, logger_factory: LoggerFactory):
    def get_logger(_, activating_type):
        return logger_factory.get_logger(activating_type.__module__ + '.' + activating_type.__name__)

    self.add_transient_by_factory(get_logger, Logger)
    return self


setattr(Container, use_logging.__name__, use_logging)
