import time

from openlock import OpenLock

if __name__ == "__main__":
    with OpenLock("test.lock", detect_stale=True, timeout=0):
        time.sleep(100)
