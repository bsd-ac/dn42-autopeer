import logging
import logging.handlers

logger = logging.getLogger("autopeer")
logger.setLevel(logging.DEBUG)
handler = logging.handlers.SysLogHandler(address="/dev/log")
formatter = logging.Formatter("%(asctime)s [%(levelname)s]   \t%(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
