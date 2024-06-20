import logging
import time

from openlock import OpenLock, Timeout

logging.basicConfig(format="%(levelname)s:%(name)s:%(process)s:%(message)s")
logger = logging.getLogger("openlock")
logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    try:
        with OpenLock("test.lock", detect_stale=True, timeout=0):
            print("Sleeping 20 seconds")
            time.sleep(20)
    except Timeout:
        pass
