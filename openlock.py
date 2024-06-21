import atexit
import logging
import os
import sys
import threading
import time
from pathlib import Path

from util import atomic_write, pid_valid

__version__ = "0.0.1"

logger = logging.getLogger(__name__)


class OpenLockException(Exception):
    pass


class Timeout(OpenLockException):
    pass


# This deals with stale lock file detection
_stale_race_delay_default = 0.5

# This deals with acquiring locks
_retry_period_default = 0.3


class FileLock:
    def __init__(
        self,
        lock_file,
        detect_stale=False,
        timeout=None,
        _retry_period=_retry_period_default,
        _stale_race_delay=_stale_race_delay_default,
    ):
        self.__lock_file = Path(lock_file)
        self.__timeout = timeout
        self.__detect_stale = detect_stale
        self.__lock = threading.Lock()
        self.__acquired = False
        self.__timer = None
        self.__retry_period = _retry_period
        self.__stale_race_delay = _stale_race_delay
        logger.debug(f"{self} created")

    def __is_stale(self):
        try:
            with open(self.__lock_file) as f:
                w = f.readlines()
                pid = int(w[0])
                name = w[1]
        except FileNotFoundError:
            return False
        except Exception:
            return True
        if not pid_valid(pid, name):
            return True
        return False

    def __remove_lock_file(self):
        try:
            os.remove(self.__lock_file)
            logger.debug(f"Lock file '{self.__lock_file}' removed")
        except OSError:
            pass

    def acquire(self, detect_stale=None, timeout=None):
        with self.__lock:
            if timeout is None:
                timeout = self.__timeout
            if detect_stale is None:
                detect_stale = self.__detect_stale
            wait_time = 0
            while True:
                if detect_stale:
                    if self.__is_stale():
                        logger.debug(f"Removing stale lock file '{self.__lock_file}'")
                        self.__remove_lock_file()
                        time.sleep(self.__stale_race_delay)
                try:
                    pid = os.getpid()
                    name = sys.argv[0]
                    atomic_write(self.__lock_file, f"{pid}\n{name}\n".encode())
                    atexit.register(self.__remove_lock_file)
                    logger.debug(f"{self} acquired")
                    self.__acquired = True
                    break
                except OSError:
                    pass

                if timeout is not None and wait_time >= timeout:
                    logger.debug(f"Unable to acquire {self}")
                    raise Timeout(f"Unable to acquire {self}") from None
                else:
                    wait_time += self.__retry_period
                    time.sleep(self.__retry_period)

    def release(self):
        with self.__lock:
            if not self.__acquired:
                logger.debug(
                    f"Ignoring attempt at releasing {self} which we do not own"
                )
                return
            self.__acquired = False
            if self.__timer is not None:
                self.__timer.cancel()
            self.__remove_lock_file()
            atexit.unregister(self.__remove_lock_file)
            logger.debug(f"{self} released")

    def locked(self):
        with self.__lock:
            return self.__acquired

    def getpid(self):
        with self.__lock:
            if self.__acquired:
                return os.getpid()
            if self.__is_stale():
                return None
            try:
                with open(self.__lock_file) as f:
                    return int(f.read().split()[0])
            except Exception:
                return None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __str__(self):
        return f"FileLock('{self.__lock_file}')"

    __repr__ = __str__
