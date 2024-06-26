import atexit
import copy
import logging
import os
import platform
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

__version__ = "1.0.7"

logger = logging.getLogger(__name__)

IS_WINDOWS = "windows" in platform.system().lower()


def pid_valid_windows(pid, name):
    cmdlet = (
        "(Get-CimInstance Win32_Process " "-Filter 'ProcessId = {}').CommandLine"
    ).format(pid)
    cmd = [
        "powershell",
        cmdlet,
    ]
    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    ) as p:
        for line in iter(p.stdout.readline, ""):
            line = line.lower()
            if name.lower() in line and "python" in line:
                return True
    return False


def pid_valid_posix(pid, name):
    # TODO fix busybox (it does not know the -p option)
    cmd = ["ps", "-f", "-p", str(pid)]

    with subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        universal_newlines=True,
    ) as p:
        for line in iter(p.stdout.readline, ""):
            if name in line and "python" in line:
                return True
    return False


def pid_valid(pid, name):
    if IS_WINDOWS:
        return pid_valid_windows(pid, name)
    else:
        return pid_valid_posix(pid, name)


class OpenLockException(Exception):
    pass


class Timeout(OpenLockException):
    pass


class InvalidRelease(OpenLockException):
    pass


class InvalidLockFile(OpenLockException):
    pass


class SlowSystem(OpenLockException):
    pass


class InvalidOption(OpenLockException):
    pass


_defaults = {
    "race_delay": 0.2,
    "tries": 2,
    "retry_period": 0.3,
    "slow_system_exception": False,
}


def get_defaults():
    return copy.copy(_defaults)


def set_defaults(**kw):
    if not set(kw.keys()).issubset(set(_defaults.keys())):
        raise InvalidOption()
    _defaults.update(kw)


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
        self.__retry_period = _defaults["retry_period"]
        self.__race_delay = _defaults["race_delay"]
        self.__tries = _defaults["tries"]
        self.__slow_system_exception = _defaults["slow_system_exception"]
        logger.debug(f"{self} created")

    def __lock_state(self, pid_valid_test=True):
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

        if not pid_valid_test:
            return {
                "state": "locked",
                "pid": pid,
                "name": name,
            }
        else:
            if not pid_valid(pid, name):
                retry = self.__lock_state(pid_valid_test=False)
                if retry["state"] == "locked" and (
                    retry["pid"] != pid or retry["name"] != name
                ):
                    logger.debug(
                        f"Lock file {self.__lock_file} has changed "
                        f"from {(pid,name)} to {(retry['pid'],retry['name'])}. "
                        f"Retrying..."
                    )
                    return self.__lock_state()
                else:
                    return {
                        "state": "unlocked",
                        "reason": "pid not valid",
                        "pid": pid,
                        "name": name,
                    }

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
            pid, name = os.getpid(), sys.argv[0]
            t = time.time()
            self.__write_lock_file(pid, name)
            tt = time.time()
            logger.debug(
                f"Lock file '{self.__lock_file}' with contents {{'pid': {pid}, "
                f"'name': '{name}'}} written in {tt-t:2f} seconds"
            )
            if tt - t >= (2 / 3) * self.__race_delay:
                message = (
                    "Slow system detected!! Consider increasing the "
                    "'race_delay' parameter "
                    f"(current value: {self.__race_delay:2f}, used: {tt-t:2f})."
                )
                logger.warning(message)
                if self.__slow_system_exception:
                    raise SlowSystem(message)
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
