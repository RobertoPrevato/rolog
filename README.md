[![Build status](https://robertoprevato.visualstudio.com/rolog/_apis/build/status/rolog-CI)](https://robertoprevato.visualstudio.com/rolog/_build/latest?definitionId=12) [![pypi](https://robertoprevato.vsrm.visualstudio.com/_apis/public/Release/badge/82014349-4c33-499c-b834-a13d016341b9/1/2)](https://pypi.org/project/rolog/) [![Test coverage](https://img.shields.io/azure-devops/coverage/robertoprevato/rolog/12.svg)](https://robertoprevato.visualstudio.com/rolog/_build?definitionId=12)

# Async friendly logging classes for Python 3

**Features:**
* logging classes using `async/await` for logs
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

## Classes and log levels

![Classes](https://raw.githubusercontent.com/RobertoPrevato/rolog/master/documentation/classes.png "Classes")

|         Class          |                                               Description                                                |
| ---------------------- | -------------------------------------------------------------------------------------------------------- |
| **LogLevel**           | Int enum: _NONE, DEBUG, INFORMATION, WARNING, ERROR, CRITICAL_                                               |
| **LogTarget**          | base for classes that are able to send log records to a certain destination                              |
| **Logger**             | class responsible for creating log records and sending them to appropriate targets, by level             |
| **LoggerFactory**      | configuration class, responsible for holding configuration of targets and providing instances of loggers |
| **LogRecord**          | log record created by loggers, sent to configured targets by a logger                                    |
| **ExceptionLogRecord** | log record created by loggers, including exception information                                           |
| **FlushLogTarget**     | abstract class, derived of `LogTarget`, handling records in groups, storing them in memory               |

### Basic use
As with the built-in `logging` module, `Logger` class is not meant to be instantiated directly, but rather obtained using a configured `LoggerFactory`.

Example:

```python
import asyncio
from rolog import LoggerFactory, Logger, LogTarget


class PrintTarget(LogTarget):

    async def log(self, record):
        await asyncio.sleep(.1)
        print(record.message, record.args, record.data)


factory = LoggerFactory()

factory.add_target(PrintTarget())

logger = factory.get_logger(__name__)

loop = asyncio.get_event_loop()

async def example():

    await logger.info('Lorem ipsum')

    # log methods support any argument and keyword argument:
    # these are stored in the instances of LogRecord, it is responsibility of LogTarget(s)
    # to handle these extra parameters as desired
    await logger.info('Hello, World!', 1, 2, 3, cool=True)

loop.run_until_complete(example())
```

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
For more information, please refer to the [dedicated page in project wiki](https://github.com/RobertoPrevato/rolog/wiki/Dependency-injection-with-rodi).

## Documentation
Please refer to documentation in the project wiki: [https://github.com/RobertoPrevato/rolog/wiki](https://github.com/RobertoPrevato/rolog/wiki).

## Develop and run tests locally
```bash
pip install -r dev_requirements.txt

# run tests using automatic discovery:
pytest
```
