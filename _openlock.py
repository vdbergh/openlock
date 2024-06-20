import atexit
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger("openlock")


class FileLockException(Exception):
    pass


class Timeout(FileLockException):
    pass


# These deal with stale lock file detection
_touch_period = 2.0
_stale_detect = 3.0
_stale_delay = 0.5

# These deal with acquiring locks
_repeat_delay = 0.3


class FileLock:
    def __init__(self, lock_file, detect_stale=False, timeout=None):
        self.__lock_file = Path(lock_file)
        self.__timeout = timeout
        self.__detect_stale = detect_stale
        self.__lock = threading.Lock()
        self.__acquired = False
        self.__timer = None
        logger.debug(f"{self} created")

    def __touch(self):
        self.__lock_file.touch()
        self.__timer = threading.Timer(_touch_period, self.__touch)
        self.__timer.start()
        if not self.__acquired:
            self.__timer.cancel()

    def __is_stale(self):
        if not self.__lock_file.exists():
            return False
        try:
            mtime = os.path.getmtime(self.__lock_file)
        except OSError as e:
            logger.error(
                "Unable to get the modification time of the lock file "
                f"{self.__lock_file}: {str(e)}"
            )
            return False
        if mtime < time.time() - _stale_detect:
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
                        time.sleep(_stale_delay)
                try:
                    fd = os.open(
                        self.__lock_file,
                        mode=0o644,
                        flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    )
                    os.write(fd, str(os.getpid()).encode())
                    os.close(fd)
                    atexit.register(self.__remove_lock_file)
                    logger.debug(f"{self} acquired")
                    self.__acquired = True
                    self.__touch()
                    break
                except FileExistsError:
                    pass

                if timeout is not None and wait_time >= timeout:
                    logger.debug(f"Unable to acquire {self}")
                    raise Timeout(f"Unable to acquire {self}") from None
                else:
                    wait_time += _repeat_delay
                    time.sleep(_repeat_delay)

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
        if self.__is_stale():
            return None
        try:
            with open(self.__lock_file) as f:
                return int(f.read())
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
