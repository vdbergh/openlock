import logging  # noqa: F401
import multiprocessing
import os
import platform
import time
import unittest

from openlock import FileLock, InvalidLockFile, InvalidRelease, Timeout, logger

IS_MACOS = "darwin" in platform.system().lower()

lock_file = "test.lock"
other_lock_file = "test1.lock"


def show(mc):
    exception = mc.exception
    logger.debug(f"{exception.__class__.__name__}: {str(mc.exception)}")


def other_process1(lock_file, reply):
    r = FileLock(lock_file)
    try:
        r.acquire(timeout=0)
    except Timeout:
        reply.value = 1


def other_process2(lock_file, reply):
    r = FileLock(lock_file)
    r.acquire(timeout=0)
    reply.value = 2


class TestOpenLock(unittest.TestCase):
    def setUp(self):
        #        logging.disable(logging.DEBUG)
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
            f.write("123\ntest_openlock.py\n")
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
        if IS_MACOS:
            # MacOS changed to 'spawn' in 3.8 which messes up this test!
            multiprocessing.set_start_method("fork")
        r = FileLock(lock_file)
        r.acquire(timeout=0)
        reply = multiprocessing.Value("d", 0)
        p = multiprocessing.Process(target=other_process1, args=(lock_file, reply))
        p.start()
        p.join()
        self.assertTrue(reply.value == 1)
        r.release()
        p = multiprocessing.Process(target=other_process2, args=(lock_file, reply))
        p.start()
        p.join()
        self.assertTrue(reply.value == 2)
        r.acquire(timeout=0)

    def test_invalid_exception(self):
        import openlock

        old_tries = openlock._tries_default
        openlock._tries_default = 0
        r = FileLock(lock_file)
        with self.assertRaises(InvalidLockFile):
            r.acquire(timeout=0)
        openlock._tries_default = old_tries


if __name__ == "__main__":
    unittest.main(verbosity=2)
