from typing import TYPE_CHECKING

from .openlock import (  # noqa: F401
    FileLock,
    InvalidLockFile,
    InvalidOption,
    InvalidRelease,
    OpenLockException,
    Timeout,
    __version__,
    get_defaults,
    logger,
    set_defaults,
)

if TYPE_CHECKING:
    from .openlock import Defaults, LockState  # noqa: F401
