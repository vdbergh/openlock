import atexit
import logging
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

__version__ = "0.0.1"

logger = logging.getLogger(__name__)

IS_WINDOWS = "windows" in platform.system().lower()


def pid_valid(pid, name):
    if IS_WINDOWS:
        cmdlet = (
            # Command line requires elevated privileges
            # "(Get-CimInstance Win32_Process -Filter 'ProcessId = {}').CommandLine"
            "Get-CimInstance Win32_Process "
            "-Filter 'ProcessId = {}'"
        ).format(pid)
        cmd = [
            "powershell",
            cmdlet,
        ]
    else:
        # for busybox these options are undocumented...
        cmd = ["ps", "-f", "-A"]

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
        bufsize=1,
        close_fds=not IS_WINDOWS,
    ) as p:

        for line in iter(p.stdout.readline, ""):
            if name in line.lower() and str(pid) in line:
                return True
    return False


class OpenLockException(Exception):
    pass


class Timeout(OpenLockException):
    pass


class InvalidRelease(OpenLockException):
    pass


class InvalidLockFile(OpenLockException):
    pass


# These deal with stale lock file detection
_race_delay_default = 0.5
_tries_default = 2

# This deals with acquiring locks
_retry_period_default = 0.3


class FileLock:
    def __init__(
        self,
        lock_file,
        timeout=None,
    ):
        self.__lock_file = Path(lock_file)
        self.__timeout = timeout
        self.__lock = threading.Lock()
        self.__acquired = False
        self.__retry_period = _retry_period_default
        self.__race_delay = _race_delay_default
        self.__tries = _tries_default
        logger.debug(f"{self} created")

    def __lock_state(self):
        try:
            with open(self.__lock_file) as f:
                s = f.readlines()
        except FileNotFoundError:
            return {"state": "unlocked", "reason": "file not found"}
        except Exception as e:
            logger.exception(f"Error accessing '{self.__lock_file}': {str(e)}")
            raise
        try:
            pid = int(s[0])
            name = s[1].strip()
        except (ValueError, IndexError):
            return {"state": "unlocked", "reason": "invalid lock file"}

        if not pid_valid(pid, name):
            return {"state": "unlocked", "reason": "pid invalid", "name": name}

        return {"state": "locked", "pid": pid, "name": name}

    def __remove_lock_file(self):
        try:
            os.remove(self.__lock_file)
            logger.debug(f"Lock file '{self.__lock_file}' removed")
        except OSError:
            pass

    def __write_lock_file(self, pid, name):
        temp_file = tempfile.NamedTemporaryFile(
            dir=os.path.dirname(self.__lock_file), delete=False
        )
        temp_file.write(f"{os.getpid()}\n{name}\n".encode())
        temp_file.close()
        os.replace(temp_file.name, self.__lock_file)

    def __acquire_once(self):
        lock_state = self.__lock_state()
        logger.debug(f"{self}: {lock_state}")
        for _ in range(0, self.__tries):
            if lock_state["state"] == "locked":
                return
            name = "python" if IS_WINDOWS else sys.argv[0]
            self.__write_lock_file(os.getpid(), name)
            time.sleep(self.__race_delay)
            lock_state = self.__lock_state()
            logger.debug(f"{self}: {lock_state}")
            if lock_state["state"] == "locked":
                if lock_state["pid"] == os.getpid():
                    logger.debug(f"{self} acquired")
                    self.__acquired = True
                    atexit.register(self.__remove_lock_file)
                return
        raise InvalidLockFile("Unable to obtain a valid lock file")

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
