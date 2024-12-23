API reference
=============

The FileLock object
-------------------

.. autoclass:: openlock.FileLock
   :class-doc-from: both
   :members: acquire, release, locked, getpid, lock_file, timeout

Exceptions
----------

.. autoexception:: openlock.OpenLockException

.. autoexception:: openlock.Timeout
   :show-inheritance:

.. autoexception:: openlock.InvalidLockFile
   :show-inheritance:

.. autoexception:: openlock.InvalidRelease
   :show-inheritance:

.. autoexception:: openlock.InvalidOption
   :show-inheritance:

Options
-------

.. autoclass:: openlock.Defaults
   :class-doc-from: both
   :show-inheritance:
   :members: race_delay, tries, retry_period

.. autofunction:: openlock.set_defaults

.. autofunction:: openlock.get_defaults

Internals
---------
		  
How does it work
^^^^^^^^^^^^^^^^

A valid lock file has two lines of text containing respectively:

* `pid`: the PID of the process holding the lock;
* `name`: the content of `argv[0]` of the process holding the lock.

A lock file is considered stale if the pair `(pid, name)` does not belong to a Python process in the process table.

A process that seeks to acquire a lock first atomically tries to create a new lock file. If this succeeds then it has acquired the lock. If it fails then this means that a lock file exists. If it is valid, i.e. not stale and syntactically valid, then this implies that the lock has already been acquired and the process will periodically retry to acquire it - subject to the `timeout` parameter. If the lock file is invalid, then the process atomically overwrites it with its own data. It sleeps `race_delay` seconds and then checks if the lock file has again been overwritten (necessarily by a different process). If not then it has acquired the lock.

Once the lock is acquired the process installs an exit handler to remove the lock file on exit.

To release the lock, the process deletes the lock file and uninstalls the exit handler.

It follows from this description that the algorithm is latency free in the common use case where there are no invalid lock files.

Issues
^^^^^^

There are no known issues in the common use case where there are no invalid lock files. In general the following is true:

* The algorithm for dealing with invalid lock files fails if a process needs more time than indicated by the `race_delay` parameter to create a new lock file after detecting the absence of a valid one. The library will issue a warning if it thinks the system is too slow for the algorithm to work correctly and it will recommend to increase the value of the `race_delay` parameter.

* Since PIDs are only unique over the lifetime of a process, it may be, although it is very unlikely, that the data `(pid, name)` matches a Python process different from the one that created the lock file. In that case the algorithm fails to recognize the lock file as stale.

History
^^^^^^^

This is a refactored version of the locking algorithm used by the worker for the Fishtest web application https://tests.stockfishchess.org/tests.
