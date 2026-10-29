"""Shared logging setup for Launchpad Digital and Condo & HOA Brief scripts.

Every script calls ``get_logger(__name__ or a short name)`` once. Log lines go to
/workspace/logs/<name>.log (never to the console) so builder stdout, which other
tools and people read, stays exactly as before.

Why a file and not the console: several builders print a single summary line
that humans and other scripts rely on; adding console log output would change
that behavior.

Secrets: never pass API keys, passwords or tokens to the logger. The helper
also masks anything that looks like a Brevo key (``xkeysib-...``) as a safety net.
"""
import atexit
import logging
import os
import re
import sys
import time

LOG_DIR = '/workspace/logs'
# A broken log call must never break or change a build, so don't print logging errors.
logging.raiseExceptions = False
_SECRET = re.compile(r'xkeysib-[A-Za-z0-9-]+|xsmtpsib-[A-Za-z0-9-]+')


class _RedactSecrets(logging.Filter):
    """Mask anything that looks like a Brevo API/SMTP key before it is written."""

    def filter(self, record):
        record.msg = _SECRET.sub('[REDACTED]', str(record.msg))
        if record.args:
            record.args = tuple(_SECRET.sub('[REDACTED]', a) if isinstance(a, str) else a
                                for a in record.args)
        return True


def get_logger(name):
    """Return a logger writing timestamped lines to /workspace/logs/<name>.log.

    Also logs the start of the run, its end with elapsed time, and any uncaught
    exception (with traceback) before Python's normal error handling runs.
    """
    log = logging.getLogger(name)
    if log.handlers:  # already configured (module imported twice)
        return log
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.FileHandler(os.path.join(LOG_DIR, f'{name}.log'))
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)-7s %(name)s pid=%(process)d: %(message)s'))
    handler.addFilter(_RedactSecrets())
    log.addHandler(handler)
    log.setLevel(logging.DEBUG)
    log.propagate = False

    started = time.time()
    log.info('start argv=%s', sys.argv[1:])

    previous_hook = sys.excepthook

    def _log_crash(exc_type, exc, tb):
        log.critical('FAILED with uncaught exception', exc_info=(exc_type, exc, tb))
        previous_hook(exc_type, exc, tb)

    sys.excepthook = _log_crash
    atexit.register(lambda: log.info('end elapsed=%.2fs', time.time() - started))
    return log
