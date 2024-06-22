import atexit
import logging
import os
import threading
import time
from pathlib import Path

__version__ = "0.0.1"

logger = logging.getLogger(__name__)


class OpenLockException(Exception):
    pass


class Timeout(OpenLockException):
    pass


class InvalidRelease(OpenLockException):
    pass


# These deal with stale lock file detection
_touch_period_default = 2.0
_stale_timeout_default = 3.0
_stale_race_delay_default = 0.5

# This deals with acquiring locks
_retry_period_default = 0.3


class FileLock:
    def __init__(
        self,
        lock_file,
        timeout=None,
        _retry_period=_retry_period_default,
        _touch_period=_touch_period_default,
        _stale_timeout=_stale_timeout_default,
        _stale_race_delay=_stale_race_delay_default,
    ):
        self.__lock_file = Path(lock_file)
        self.__timeout = timeout
        self.__lock = threading.Lock()
        self.__acquired = False
        self.__timer = None
        self.__retry_period = _retry_period
        self.__touch_period = _touch_period
        self.__stale_timeout = _stale_timeout
        self.__stale_race_delay = _stale_race_delay
        logger.debug(f"{self} created")

    def __touch(self):
        self.__lock_file.touch()
        self.__timer = threading.Timer(self.__touch_period, self.__touch)
        self.__timer.daemon = True
        self.__timer.start()
        if not self.__acquired:
            self.__timer.cancel()

    def __lock_state(self):
        try:
            fd = os.open(self.__lock_file, mode=0o444, flags=os.O_RDONLY)
            st = os.stat(fd)
            if st.st_mtime < time.time() - self.__stale_timeout:
                os.close(fd)
                return {"state": "unlocked"}
            s = os.read(fd, st.st_size)
            os.close(fd)
        except FileNotFoundError:
            return {"state": "unlocked"}
        except OSError as e:
            logger.error(
                f"__lock_state: Error accessing '{self.__lock_file}': {str(e)}"
            )
            raise
        try:
            pid = int(s)
        except ValueError:
            return {"state": "invalid"}
        return {"state": "locked", "pid": pid}

    def __remove_lock_file(self):
        try:
            os.remove(self.__lock_file)
            logger.debug(f"Lock file '{self.__lock_file}' removed")
        except OSError:
            pass

    def __acquire_once(self):
        lock_state = self.__lock_state()
        logger.debug(f"{self}: {lock_state}")
        while True:
            if lock_state["state"] == "locked":
                return
            with open(self.__lock_file, "w") as f:
                f.write(str(os.getpid()))
            time.sleep(self.__stale_race_delay)
            lock_state = self.__lock_state()
            logger.debug(f"{self}: {lock_state}")
            if lock_state["state"] == "locked":
                if lock_state["pid"] == os.getpid():
                    logger.debug(f"{self} acquired")
                    self.__acquired = True
                    self.__touch()
                    atexit.register(self.__remove_lock_file)
                    break
                else:
                    return

    def acquire(self, timeout=None):
        if timeout is None:
            timeout = self.__timeout
        start_time = time.time()
        with self.__lock:
            while True:
                if not self.__acquired:
                    self.__acquire_once()
                    if self.__acquired:
                        break
                now = time.time()
                if timeout is not None and now - start_time >= timeout:
                    raise Timeout(f"Unable to acquire {self}")
                time.sleep(self.__retry_period)

    def release(self):
        with self.__lock:
            if not self.__acquired:
                raise InvalidRelease(f"Attempt at releasing {self} which we do not own")
            self.__acquired = False
            if self.__timer is not None:
                self.__timer.cancel()
            self.__remove_lock_file()
            atexit.unregister(self.__remove_lock_file)
            logger.debug(f"{self} released")

    def locked(self):
        with self.__lock:
            return self.__lock_state()["state"] == "locked"

    def getpid(self):
        with self.__lock:
            if self.__acquired:
                return os.getpid()
            lock_state = self.__lock_state()
            if lock_state["state"] == "locked":
                return lock_state["pid"]
            else:
                return None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()

    def __str__(self):
        return f"FileLock('{self.__lock_file}')"

    __repr__ = __str__
