import argparse
import grp
import os
import pwd
import socket
import sys
import time
import tomllib

import uvicorn

from . import settings, sp
from .logger import logger
from .peer_manager import PeerManager
from .webapp import app

parser = argparse.ArgumentParser()
parser.add_argument(
    "-f",
    metavar="file",
    type=str,
    help="config file, see `man 5 autopeer.conf` for details",
    default="/etc/autopeer.conf",
)
parser.add_argument("-n", action="store_true", help="configtest mode")
parser.add_argument(
    "-d",
    help="debug level",
    choices=["debug", "info", "warn", "error", "critical"],
    default="info",
)


def main():
    args = parser.parse_args()
    logger.setLevel(args.d.upper())

    with open(args.f, "rb") as f:
        config = tomllib.load(f)

    pid = os.fork()
    if pid == 0:
        # child process
        sp[0].close()

        if not "host" in config["uvicorn"]:
            config["uvicorn"]["host"] = "127.0.0.1"
        if not "port" in config["uvicorn"]:
            config["uvicorn"]["port"] = 8000
        config["uvicorn"]["workers"] = 1

        gid = grp.getgrnam(config["autopeer"]["group"]).gr_gid
        uid = pwd.getpwnam(config["autopeer"]["user"]).pw_uid

        os.setgid(gid)
        os.setuid(uid)

        settings.initialize(config["autopeer"])
        uvicorn.run(app, **config["uvicorn"])
    else:
        # parent process
        logger.debug("Parent process")

        sp[1].close()
        pm = PeerManager(sp[0])
        pm.run()
    os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
