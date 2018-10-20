from rodi import ServiceCollection
from rolog import LoggerFactory
from rolog.tests.one import One
from rolog.tests.one.two import Two
from rolog.tests.one.two.three import Three
from rolog.rodi import use_logging


def test_get_logger_by_name_of_activated_class():
    services = ServiceCollection()
    factory = LoggerFactory()

    use_logging(services, factory)

    services.add_exact_singleton(One)
    services.add_exact_transient(Two)
    services.add_exact_scoped(Three)

    provider = services.build_provider()

    one = provider.get(One)
    two = provider.get(Two)
    three = provider.get(Three)

    assert one is not None
    assert two is not None
    assert three is not None

    assert one.logger is not None
    assert two.logger is not None
    assert three.logger is not None

    assert 'rolog.tests.one.One' == one.logger.name
    assert 'rolog.tests.one.two.Two' == two.logger.name
    assert 'rolog.tests.one.two.three.Three' == three.logger.name
