from rolog import LoggerFactory, Logger

try:
    from rodi import ServiceCollection
except ImportError:

    def use_logging(services: ServiceCollection, logger_factory: LoggerFactory):
        raise Exception('Missing dependency: `rodi`. To use this method, please install `rodi`.')

else:

    def use_logging(self: ServiceCollection, logger_factory: LoggerFactory):
        def get_logger(_, activating_type):
            return logger_factory.get_logger(activating_type.__module__ + '.' + activating_type.__name__)

        self.add_transient_by_factory(get_logger, Logger)
        return self

    setattr(ServiceCollection, use_logging.__name__, use_logging)
