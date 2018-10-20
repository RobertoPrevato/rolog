# Async friendly logging classes for Python 3

**Features:**
* `async/await` friendly logging classes
* handling of six logging levels, like in built-in logging module
* built-in support for flushing of log records (e.g. making a web request, or writing to a database, every __n__ records)
* flushing supports max retries, configurable delays, number of attempts, and fallback target in case of failure
* support for several targets per logger
* can be used to asynchronously log to different destinations (for example, web api integration, DBMS, etc.)
* logged records support any kind of desired arguments and data structures
* completely abstracted from __destination__ of log entries
* can be used with built-in `logging` module, for sync logging and to [use built-in logging classes](https://docs.python.org/3/library/logging.handlers.html#module-logging.handlers)
* integrated with [rodi dependency injection library](https://pypi.org/project/rodi/), to support injection of loggers by activated class name

## Installation

```bash
pip install rolog
```

## Logging levels
`rolog` implements logging levels compatible with those from built-in logging module, having the same numeric value,
and the same name (except for __NONE__, which in the built-in library is called "NOTSET").
__NONE, DEBUG, INFORMATION, WARNING, ERROR, CRITICAL__.

```python
class LogLevel(IntEnum):
    NONE = 0
    DEBUG = 10
    INFORMATION = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50
```

## Classes

![Classes](https://raw.githubusercontent.com/RobertoPrevato/rolog/master/documentation/classes.png "Classes")

* LoggerFactory
* Logger
* LogTarget
* LogRecord
* ExceptionLogRecord 

### Basic use
As with the built-in `logging` module, `Logger` class is not meant to be instantiated directly, but rather obtained using a configured `LoggerFactory`.

## Flushing targets
`rolog` has built-in support for log targets that flush messages in groups, this is necessary to optimize for example
reducing the number of web requests when sending log records to a web api, or enabling bulk-insert inside a database.
Below is an example of flush target class that sends log records to some web api, in groups of `500`:

```python
from typing import List
from rolog import FlushLogTarget, LogRecord


class SomeLogApiFlushLogTarget(FlushLogTarget):

    def __init__(self, http_client):
        super().__init__()
        self.http_client = http_client

    async def log_records(self, records: List[LogRecord]):
        # NB: implement here your own logic to make web requests to send log records
        # to a web api, such as Azure Application Insights 
        # (see for example https://pypi.org/project/asynapplicationinsights/)
        pass
```

Flush targets handle retries with configurable and progressive delays, when logging a group of records fails.
By default, in case of failure a flush target tries to log records __3 times__, using a progressive delay of __0.6 seconds * attempt number__,
finally falling back to a configurable fallback target if logging always failed. Warning messages are issued, using built-in
[`Warnings`](https://docs.python.org/3.1/library/warnings.html) module to notify of these failures.

These parameters are configurable using constructor parameters `fallback_target`, `max_size`, `retry_delay`, `progressive_delay`.

```python
class FlushLogTarget(LogTarget, ABC):
    """Base class for flushing log targets: targets that send the log records
    (created by loggers) to the appropriate destination in groups."""

    def __init__(self,
                 queue: Optional[Queue]=None,
                 max_length: int=500,
                 fallback_target: Optional[LogTarget]=None,
                 max_retries: int=3,
                 retry_delay: float=0.6,
                 progressive_delay: bool=True):
```

### Flushing when application stops
Since flushing targets hold log records in memory before flushing them, it's necessary to flush when an application stops.
Assuming that a single `LoggerFactory` is configured in the configuration root of an application, this 
can be done conveniently, by calling the `dispose` method of the logger factory.

```python
# on application shutdown:
await logger_factory.dispose()

``` 

## Dependency injection
`rolog` is integrated with [rodi dependency injection library](https://pypi.org/project/rodi/), to support injection of loggers per activated class name.
When a class that expects a parameter of `rolog.Logger` type is activated, it receives a logger for the category of the class name itself.

## Documentation
Please refer to documentation in the project Wiki: [https://github.com/RobertoPrevato/rolog/wiki](https://github.com/RobertoPrevato/rolog/wiki).
