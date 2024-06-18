import logging
import time

from openlock import OpenLock

logger = logging.getLogger("openlock")
logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    with OpenLock("test.lock", detect_stale=True, timeout=0):
        print("Sleeping 20 seconds")
        time.sleep(10)
