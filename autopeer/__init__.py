import logging
import logging.handlers
import socket
from typing import Dict

from cachetools import TTLCache

from .settings import Settings

cache: TTLCache = TTLCache(maxsize=1000, ttl=5)
sp = socket.socketpair()
max_bytes = 8
settings: Settings = Settings()
