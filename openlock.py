import atexit
import logging
import os
import threading
import time
from pathlib import Path

logging.basicConfig()
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)


class Timeout(Exception):
    pass


# These deal with stale lock file detection
_touch_period = 2.0
_stale_detect = 7.0
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
        try:
            atime = os.path.getatime(self.__lock_file)
        except Exception:
            return False
        if atime < time.time() - _stale_detect:
            return True
        return False

    def __remove_lock_file(self):
        try:
            os.remove(self.__lock_file)
            logger.debug("Log file removed")
        except Exception:
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
                        os.remove(self.__lock_file)
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
                except Exception:
                    if timeout is not None and wait_time >= timeout:
                        raise Timeout("Unable to acquire lock") from None
                    else:
                        wait_time += _repeat_delay
                        time.sleep(_repeat_delay)

    def release(self):
        with self.__lock:
            self.__acquired = False
            self.__remove_lock_file()
            atexit.unregister(self.__remove_lock_file)
            logger.debug("Lock released")

    def __enter__(self):
        self.acquire()

    def __exit__(self, exc_type, exc_value, traceback):
        self.release()
