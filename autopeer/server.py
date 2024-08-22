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

    settings.initialize(config)

    pid = os.fork()
    if pid == 0:
        # child process
        sp[0].close()

        gid = grp.getgrnam(config["group"]).gr_gid
        uid = pwd.getpwnam(config["user"]).pw_uid

        if "chroot" in config:
            os.chroot(config["chroot"])
        os.chdir("/")

        os.setgid(gid)
        os.setuid(uid)

        uvicorn.run(app, host=config["host"], port=config["port"], workers=1)
    else:
        # parent process
        logger.debug("Parent process")

        sp[1].close()
        pm = PeerManager(sp[0])
        pm.run()
    os.waitpid(pid, 0)


if __name__ == "__main__":
    main()
