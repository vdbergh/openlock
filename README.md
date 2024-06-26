# openlock

A locking library not depending on inter-process locking primitives in the OS.

## API

- `FileLock(lock_file, timeout=None)`. Constructor. The optional `timeout` argument is the default for the corresponding argument of `acquire()` (see below). A `FileLock` object supports the context manager protocol.
- `FileLock.acquire(timeout=None)`. Attempts to acquire the lock. The optional `timeout` argument specifies the maximum waiting time in seconds before a `Timeout` exception is raised.
- `FileLock.release()`. Releases the lock. May raise and `InvalidRelease` exception.
- `FileLock.locked()`. Indicates if the lock is held by a process.
- `FileLock.getpid()`. The PID of the process that holds the lock, if any. Otherwise returns `None`.

## How does it work

A valid lock file has two lines of text containing respectively:

- `pid`: the PID of the process holding the lock;
- `name`: the content of `argv[0]` of the process holding the lock.

A lock file is considered stale if the pair `(pid, name)` does not belong to a Python process in the process table.

A process that seeks to acquire a lock first looks for an existing valid lock file. If it exists then this means that the lock has already been acquired and the process will periodically retry to acquire it - subject to the `timeout` parameter. If there is no lock file, or if it is stale or unparsable, then the process atomically creates a new lock file with its own data. It sleeps 0.5 seconds (configurable) and then checks if the lock file has been overwritten by a different process. If not then it has acquired the lock.

## Issues

- The algorithm fails if a process needs more than 0.5 seconds to create a new lock file after detecting the absence of a valid one.

- Although it is very unlikely, it may be that the data `(pid, name)` matches a different Python process since PIDs are only unique over the lifetime of a process. In that case the algorithm fails to recognize the lock file as stale.

## History

This is a refactored version of the locking algorithm used by the worker for the Fishtest web application <https://tests.stockfishchess.org/tests>.
