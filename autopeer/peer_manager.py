import json
import os
import socket
import subprocess
from typing import Generator

from . import logger, max_bytes

# from .templates import bgp_default, bgp_listener, bgp_peer, hostname_wg


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
            if "command" not in cmd:
                resp = {"success": False, "error": "No command specified"}
            elif cmd["command"] == "create":
                resp = self.peer_create(cmd)
            elif cmd["command"] == "delete":
                resp = self.peer_delete(cmd)
            else:
                resp = {"success": False, "error": "Invalid command"}
            self.send(resp)

    def peer_create(self, info: dict) -> dict:
        # try:
        #     wgid = info["wgid"]
        # except KeyError:
        #     return {"success": False, "error": "No 'wgid' specified"}

        # hostname_info = hostname_wg.render()
        # hostname_file = f"/etc/hostname.wg{wgid}"

        # with open(hostname_file, "w") as f:
        #     f.write(hostname_info)

        # # test the config
        # sp = subprocess.run(
        #     ["/bin/sh", "/etc/netstart", "-n", f"wg{wgid}"], capture_output=True
        # )
        # if sp.returncode:
        #     # remove the hostname file
        #     os.unlink(hostname_file)
        #     return {"success": False, "error": sp.stderr.decode()}

        # # create peers BGP config
        # bgp_peer_file = f"/etc/bgpd.d/peer-{info.new_peer.ASN}.conf"
        # bgp_listener_file = f"/etc/bgpd.d/listener-{info.new_peer.ASN}.conf"

        # with open(bgp_peer_file, "w") as f:
        #     f.write(bgp_peer.render(peers=[info.new_peer]))

        # with open(bgp_listener_file, "w") as f:
        #     f.write(bgp_listener.render(peers=[info.new_peer]))

        return {"success": True}

    def peer_delete(self, info: dict) -> dict:
        return {"success": True}


# class BGPD:
#     @staticmethod
#     def peers_available() -> Generator[int]:
#         # find all file names of the form /etc/bgpd.d/peer-*.conf
#         for file in os.listdir("/etc/bgpd.d"):
#             if file.startswith("peer-") and file.endswith(".conf"):
#                 try:
#                     ASN = int(file[5:-5])
#                     yield ASN
#                 except ValueError:
#                     logger.error(f"Invalid peer file: {file}")

#     @staticmethod
#     def peers_enabled() -> Generator[int]:
#         # find all lines in /etc/bgpd.d/peers-enabled.conf
#         with open("/etc/bgpd.d/peers-enabled.conf") as f:
#             for line in f:
#                 # line is of the form /etc/bgpd.d/peer-*.conf
#                 try:
#                     ASN = int(line[17:-5])
#                     yield ASN
#                 except ValueError:
#                     logger.error(f"Invalid peer file: {line}")

#     @staticmethod
#     def peer_enable(peer: int) -> None:
#         for asn in BGPD.peers_enabled():
#             if asn == peer:
#                 return
#         with open("/etc/bgpd.d/peers-enabled.conf", "a") as f:
#             f.write(f"/etc/bgpd.d/peer-{peer}.conf\n")

#     @staticmethod
#     def peer_disable(peer: int) -> None:
#         enabled = list(BGPD.peers_enabled())
#         with open("/etc/bgpd.d/peers-enabled.conf", "w") as f:
#             for asn in enabled:
#                 if asn != peer:
#                     f.write(f"/etc/bgpd.d/peer-{asn}.conf\n")
