# openlock

A locking library not depending on inter-process locking primitives in the OS.

## Api

- `FileLock(lock_file, timeout=None)`. Constructor. The optional `timeout` argument is the default for the corresponding argument of `acquire()` (see below).
- `FileLock.acquire(timeout=None)`. Attempts to acquires the lock. The optional `timeout` argument specifies the maximum waiting time before a `Timeout` exception is thrown.
- `FileLock.release()`. Releases the lock.
- `FileLock.locked()`. Indicates if the lock is held by a process.
- `FileLock.getpid()`. The PID of the process that holds the lock, if any. Otherwise returns `None`.

## How does it work

A valid lock file has two lines of text containing respectively:

- `pid`: the PID of the process holding the lock;
- `name`: the content of `argv[0]` of the process holding the lock.

A lock file is considered stale if the pair `(pid, name)` does not belong to a process in the process table.

A process that seeks to acquire a lock first looks for an existing valid lock file. If there is no lock file, or if it is stale or unparsable, then the process atomically creates a new lock file with its own data. It then sleeps 0.5 seconds (configurable) and checks if the lock file has not been overwritten by a different process. If not then it has acquired the lock.

## Issues

The algorithm fails if a process need more than 0.5 seconds between detecting the absence of a valid lock file and creating a new one.

## History

This is a refactored version of the locking algorithm used by the worker for the Fishtest web application <https://tests.stockfishchess.org/tests>.
