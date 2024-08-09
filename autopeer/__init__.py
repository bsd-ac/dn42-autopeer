import logging
import logging.handlers
from typing import Dict

logger: logging.Logger = logging.getLogger("autopeer")
logger.setLevel(logging.DEBUG)

formatter: logging.Formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s]\t%(name)s: %(message)s"
)

syslog_handler: logging.handlers.SysLogHandler = logging.handlers.SysLogHandler(
    address="/dev/log"
)
syslog_handler.setFormatter(formatter)
logger.addHandler(syslog_handler)

console_handler: logging.StreamHandler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


cache: Dict[int, str] = {}
