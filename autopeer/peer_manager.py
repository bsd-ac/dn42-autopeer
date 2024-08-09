import json
import socket

from . import logger, max_bytes


class PeerManager:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock

    def recv(self):
        cmd_bytes = self.sock.recv(max_bytes)
        if not cmd_bytes:
            logger.critical("Connection closed while receiving command length")
            raise ConnectionError
        logger.debug(f"Received command length bytes: {cmd_bytes}")

        try:
            cmd_len = int.from_bytes(cmd_bytes)
            logger.debug(f"Received command length: {cmd_len}")
        except ValueError:
            logger.critical(f"Invalid command length: {cmd_bytes}")
            raise ValueError

        cmd = self.sock.recv(cmd_len)
        if not cmd:
            logger.critical("Connection closed while receiving command")
            raise ConnectionError
        logger.debug(f"Received command bytes: {cmd}")

        jcmd = json.loads(cmd)
        logger.debug(f"Received command: {jcmd}")
        return jcmd

    def send(self, cmd: dict):
        cmd_bytes = json.dumps(cmd).encode()
        cmd_len = len(cmd_bytes).to_bytes(max_bytes)
        self.sock.send(cmd_len)
        self.sock.send(cmd_bytes)

    def run(self):
        while True:
            try:
                cmd = self.recv()
            except ConnectionError:
                break
            except ValueError:
                continue

            resp = {"message": "OK"}
            self.send(resp)
