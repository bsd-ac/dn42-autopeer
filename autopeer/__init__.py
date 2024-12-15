import ipaddress
import socket

from cachetools import TTLCache

from autopeer.settings import Settings

token_cache: TTLCache = TTLCache(maxsize=1000, ttl=60)  # 1 minute
gpg_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)  # 5 minutes
sp = socket.socketpair()
max_bytes = 8
settings: Settings = Settings()

WG_KEYLEN = 44

MAX_IP_TRIES = 10

DN42_SUBNET4 = ipaddress.IPv4Network("172.20.0.0/14")
DN42_SUBNET6 = ipaddress.IPv6Network("fd00::/8")

LL_SUBNET4 = ipaddress.IPv4Network("169.254.0.0/16")
LL_SUBNET6 = ipaddress.IPv6Network("fe80::/10")
