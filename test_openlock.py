import logging  # noqa: F401
import os
import platform
import subprocess
import sys
import time
import unittest

from openlock import (
    FileLock,
    InvalidLockFile,
    InvalidRelease,
    Timeout,
    get_defaults,
    logger,
    set_defaults,
)

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(process)s:%(message)s")
logger.setLevel(logging.DEBUG)

IS_MACOS = "darwin" in platform.system().lower()
IS_WINDOWS = "windows" in platform.system().lower()

lock_file = "test.lock"
other_lock_file = "test1.lock"


def show(mc):
    exception = mc.exception
    logger.debug(f"{exception.__class__.__name__}: {str(mc.exception)}")


class TestOpenLock(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.DEBUG)
        for L in (lock_file, other_lock_file):
            try:
                os.remove(L)
            except OSError:
                pass

    def test_acquire_release(self):
        r = FileLock(lock_file)
        self.assertFalse(r.locked())
        r.acquire(timeout=0)
        self.assertTrue(os.path.exists(lock_file))
        self.assertTrue(r.locked())
        self.assertTrue(r.getpid() == os.getpid())
        r.release()
        self.assertFalse(os.path.exists(lock_file))
        self.assertFalse(r.locked())

    def test_double_acquire(self):
        r = FileLock(lock_file)
        r.acquire(timeout=0)
        with self.assertRaises(Timeout):
            r.acquire(timeout=0)

    def test_invalid_release(self):
        r = FileLock(lock_file)
        with self.assertRaises(InvalidRelease):
            r.release()
        r.acquire(timeout=0)
        r.release()
        with self.assertRaises(InvalidRelease):
            r.release()

    def test_invalid_lock_file(self):
        with open(lock_file, "w") as f:
            pass
        r = FileLock(lock_file)
        r.acquire(timeout=0)
        r.release()
        with open(lock_file, "w") as f:
            f.write(f"{os.getpid()}\ndummy.py\n")
        r.acquire(timeout=0)
        self.assertTrue(os.getpid() == r.getpid())
        r.release()
        with open(lock_file, "w") as f:
            f.write("1\ntest_openlock.py\n")
        r.acquire(timeout=0)
        self.assertTrue(os.getpid() == r.getpid())
        r.release()

    def test_timeout(self):
        r = FileLock(lock_file)
        t = time.time()
        r.acquire(timeout=0)
        with self.assertRaises(Timeout):
            r.acquire(timeout=2)
        self.assertTrue(time.time() - t >= 2)

    def test_different_lock_files(self):
        r = FileLock(lock_file)
        s = FileLock(other_lock_file)
        r.acquire(timeout=0)
        s.acquire(timeout=0)
        self.assertTrue(r.locked())
        self.assertTrue(s.locked())

    def test_second_process(self):
        r = FileLock(lock_file)
        r.acquire(timeout=0)
        p = subprocess.run(
            [sys.executable, "_helper.py", lock_file, "1"], stdout=subprocess.PIPE
        )
        self.assertTrue(p.stdout.decode().strip() == "1")
        r.release()
        p = subprocess.Popen(
            [sys.executable, "_helper.py", lock_file, "2"], stdout=subprocess.PIPE
        )
        time.sleep(1)
        with self.assertRaises(Timeout):
            r.acquire(timeout=0)
        out, err = p.communicate()
        self.assertTrue(out.decode().strip() == "2")
        r.acquire(timeout=0)

    def test_invalid_exception(self):
        old_tries = get_defaults()
        set_defaults(tries=0)
        r = FileLock(lock_file)
        with self.assertRaises(InvalidLockFile):
            r.acquire(timeout=0)
        set_defaults(**old_tries)


if __name__ == "__main__":
    unittest.main(verbosity=2)
