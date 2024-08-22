import logging
import logging.handlers
import socket
from typing import Dict

from .settings import Settings

cache: Dict[int, str] = {}
sp = socket.socketpair()
max_bytes = 8
settings: Settings = Settings()
