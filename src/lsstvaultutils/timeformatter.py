import logging
import time
from typing import Optional


class TimeFormatter(logging.Formatter):
    """Time formatter that does milliseconds.
    https://stackoverflow.com/questions/6290739/\
     python-logging-use-milliseconds-in-time-format
    """

    def formatTime(
        self, record: logging.LogRecord, datefmt: Optional[str] = None
    ) -> str:
        ct = self.converter(record.created)
        if datefmt:
            if "%F" in datefmt:
                msec = "%03d" % record.msecs
                datefmt = datefmt.replace("%F", msec)
            s = time.strftime(datefmt, ct)
        else:
            t = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s = "%s,%03d" % (t, record.msecs)
        return s


def getLogger(name: str = __name__, debug: bool = False) -> logging.Logger:
    """Convenience function to return configured logger with milliseconds."""
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    ch = logging.StreamHandler()
    if debug:
        ch.setLevel(logging.DEBUG)
    formatter = TimeFormatter(
        "%(asctime)s [%(levelname)s] %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S.%F %Z(%z)",
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger
