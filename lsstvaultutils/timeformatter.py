import logging
import time


class TimeFormatter(logging.Formatter):
    """Time formatter that does milliseconds.
    https://stackoverflow.com/questions/6290739/\
     python-logging-use-milliseconds-in-time-format
    """

    def formatTime(self, record, datefmt=None):
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
