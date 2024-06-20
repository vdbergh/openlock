import atexit
import logging
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger("openlock")


class OpenLockException(Exception):
    pass


class Timeout(OpenLockException):
    pass


# These deal with stale lock file detection
_touch_period = 2.0
_stale_detect = 3.0
_stale_delay = 0.5

# These deal with acquiring locks
_repeat_delay = 0.3


class OpenLock:
    def __init__(self, lock_file, detect_stale=False, timeout=None):
        self.__lock_file = Path(lock_file)
        self.__timeout = timeout
        self.__detect_stale = detect_stale
        self.__lock = threading.Lock()
        self.__acquired = False
        self.__repeat_touch = threading.Thread(target=self.__touch, daemon=True)
        self.__repeat_touch.start()
        logger.debug("Lock created")

    def __touch(self):
        while True:
            if self.__acquired:
                self.__lock_file.touch()
            time.sleep(_touch_period)

    def __is_stale(self):
        if not self.__lock_file.exists():
            return False
        try:
            mtime = os.path.getmtime(self.__lock_file)
        except OSError as e:
            logger.error(
                "Unable to get the access time of the lock file "
                f"{self.__lock_file}: {str(e)}"
            )
            return False
        if mtime < time.time() - _stale_detect:
            return True
        return False

    def __remove_lock_file(self):
        try:
            os.remove(self.__lock_file)
            logger.debug("Lock file removed")
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
                        logger.debug("Removing stale lock file")
                        self.__remove_lock_file()
                        time.sleep(_stale_delay)
                try:
                    fd = os.open(
                        self.__lock_file, mode=0o644, flags=os.O_CREAT | os.O_EXCL
                    )
                    os.close(fd)
                    atexit.register(self.__remove_lock_file)
                    logger.debug("Lock acquired")
                    self.__acquired = True
                    break
                except FileExistsError:
                    pass

                if timeout is not None and wait_time >= timeout:
                    logger.debug("Unable to acquire lock")
                    raise Timeout("Unable to acquire lock") from None
                else:
                    wait_time += _repeat_delay
                    time.sleep(_repeat_delay)

    def release(self):
        with self.__lock:
            if not self.__acquired:
                logger.debug("Ignoring attempt at releasing a lock we do not own")
                return
            self.__acquired = False
            self.__remove_lock_file()
            atexit.unregister(self.__remove_lock_file)
            logger.debug("Lock released")

    def locked(self):
        return self.__acquired

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
