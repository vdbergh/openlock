# openlock

A locking library not depending on inter-process locking primitives in the OS.

## API

- `FileLock(lock_file="openlock.lock", timeout=None)`. Constructor. The optional `timeout` argument is the default for the corresponding argument of `acquire()` (see below). A `FileLock` object supports the context manager protocol.
- `FileLock.acquire(timeout=None)`. Attempts to acquire the lock. The optional `timeout` argument specifies the maximum waiting time in seconds before a `Timeout` exception is raised.
- `FileLock.release()`. Releases the lock. May raise an `InvalidRelease` exception.
- `FileLock.locked()`. Indicates if the lock is held by a process.
- `FileLock.getpid()`. The PID of the process that holds the lock, if any. Otherwise returns `None`.
- `FileLock.lock_file`. The name of the lock file.
- `FileLock.timeout`. The value of the timeout parameter.
- `openlock.set_defaults(**kw)`. Sets default values for the internal parameters. Currently `tries`, `retry_period`, `race_delay` and `slow_system_exception` with values of 2, 0.3s, 0.2s and False respectively.
- `openlock.get_defaults()`. Returns a dictionary with the default values for the internal parameters.

## How does it work

A valid lock file has two lines of text containing respectively:

- `pid`: the PID of the process holding the lock;
- `name`: the content of `argv[0]` of the process holding the lock.

A lock file is considered stale if the pair `(pid, name)` does not belong to a Python process in the process table.

A process that seeks to acquire a lock first looks for an existing valid lock file. If it exists then this means that the lock has already been acquired and the process will periodically retry to acquire it - subject to the `timeout` parameter. If there is no lock file, or if it is stale or unparsable, then the process atomically creates a new lock file with its own data. It sleeps 0.2 seconds (configurable) and then checks if the lock file has been overwritten by a different process. If not then it has acquired the lock.

## Issues

- The algorithm fails if a process needs more than 0.2 seconds to create a new lock file after detecting the absence of a valid one. The library will issue a warning if it thinks the system is too slow for the algorithm to work correctly and it will recommend to increase the value of the `race_delay` parameter.

- Although it is very unlikely, it may be that the data `(pid, name)` matches a different Python process since PIDs are only unique over the lifetime of a process. In that case the algorithm fails to recognize the lock file as stale.

## History

This is a refactored version of the locking algorithm used by the worker for the Fishtest web application <https://tests.stockfishchess.org/tests>.
