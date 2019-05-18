from rodi import Container
from rolog import LoggerFactory, Logger
from rolog.rodi import use_logging


# example classes using loggers:
class One:
    def __init__(self, logger: Logger):
        self.logger = logger


class Two:
    def __init__(self, logger: Logger):
        self.logger = logger


def test_get_logger_by_name_of_activated_class():
    container = Container()
    factory = LoggerFactory()

    use_logging(container, factory)

    container.add_exact_transient(One)
    container.add_exact_transient(Two)

    services = container.build_provider()

    one = services.get(One)
    two = services.get(Two)

    assert one is not None
    assert two is not None

    assert one.logger is not None
    assert two.logger is not None

    base_namespace = One.__module__ + '.'

    assert base_namespace + 'One' == one.logger.name
    assert base_namespace + 'Two' == two.logger.name
