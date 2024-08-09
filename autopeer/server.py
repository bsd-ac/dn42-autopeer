import logging
import os
import sys

import uvicorn
import zmq
import zmq.asyncio

from . import logger
from .webapp import app


def main():
    # check if we are root, else quit
    if os.geteuid() != 0:
        logger("This script must be run as root")
        sys.exit(1)

    context = zmq.Context()

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
