import logging
import signal
import sys
import time

# Replace _openlock by openlock if the package
# has been properly installed.
from _openlock import OpenLock, Timeout

logging.basicConfig(format="%(asctime)s:%(levelname)s:%(name)s:%(process)s:%(message)s")
logger = logging.getLogger("openlock")
logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    try:
        with OpenLock("test.lock", detect_stale=True, timeout=0) as L:
            logger.debug(f"Locked by PID={L.getpid()}")

            assert L.locked()

            def cleanup(signum, frame):
                L.release()
                sys.exit()

            signal.signal(signal.SIGTERM, cleanup)
            signal.signal(signal.SIGINT, cleanup)
            logger.info("Sleeping 20 seconds")
            time.sleep(20)
    except Timeout:
        pass

    assert not L.locked()
