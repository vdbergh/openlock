import logging
import os
import time
import unittest

from openlock import FileLock, InvalidRelease, Timeout

lock_file = "test.lock"


def show(mc):
    exception = mc.exception
    print(f"{exception.__class__.__name__}: {str(mc.exception)}")


class TestOpenLock(unittest.TestCase):
    def setUp(self):
        logging.disable(logging.DEBUG)
        try:
            os.remove(lock_file)
        except OSError:
            pass

    def test_acquire_release(self):
        r = FileLock(lock_file)
        self.assertFalse(r.locked())
        r.acquire()
        self.assertTrue(r.locked())
        self.assertTrue(r.getpid() == os.getpid())
        r.release()
        self.assertFalse(r.locked())

    def test_double_acquire(self):
        r = FileLock(lock_file)
        r.acquire()
        with self.assertRaises(Timeout) as mc:
            r.acquire(timeout=0)
        show(mc)

    def test_invalid_release(self):
        r = FileLock(lock_file)
        with self.assertRaises(InvalidRelease) as mc:
            r.release()
        show(mc)
        r.acquire()
        r.release()
        with self.assertRaises(InvalidRelease) as mc:
            r.release()
        show(mc)

    def test_invalid_lock_file(self):
        with open(lock_file, "w") as f:
            pass
        r = FileLock(lock_file)
        r.acquire()
        r.release()
        with open(lock_file, "w") as f:
            f.write("123\ndummy.py\n")
        r.acquire()
        self.assertTrue(os.getpid() == r.getpid())
        r.release()

    def test_timeout(self):
        r = FileLock(lock_file)
        t = time.time()
        r.acquire()
        with self.assertRaises(Timeout) as mc:
            r.acquire(timeout=2)
        show(mc)
        self.assertTrue(time.time() - t >= 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
