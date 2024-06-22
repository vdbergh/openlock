import logging
import signal
import sys
import time

from openlock import FileLock, Timeout

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(process)s:%(message)s")
logger = logging.getLogger("openlock")
logger.setLevel(logging.DEBUG)


def cleanup(signum, frame):
    sys.exit()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    try:
        with FileLock("test.lock", timeout=0) as L:
            logger.debug(f"{L} locked by PID={L.getpid()}")

            assert L.locked()

            logger.info("Sleeping 20 seconds")
            time.sleep(20)
    except Timeout as e:
        logger.debug(e)
