import base64
import ipaddress
import json
import os
import socket
import subprocess
from typing import Generator, Optional

from fastapi import HTTPException

from . import max_bytes
from .logger import logger
from .schemas import PeerInfo
from .templates import bgpd_conf, hostname_wg


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
            try:
                if "command" not in cmd:
                    resp = {"success": False, "error": "No command specified"}
                elif cmd["command"] == "bgp_update":
                    resp = self.bgp_update(cmd)
                elif cmd["command"] == "wg_exists":
                    resp = self.wg_exists(cmd)
                elif cmd["command"] == "wg_create":
                    resp = self.wg_create(cmd)
                elif cmd["command"] == "wg_delete":
                    resp = self.wg_delete(cmd)
                else:
                    resp = {"success": False, "error": "Invalid command"}
                self.send(resp)
            except Exception as e:
                logger.error(f"Failed to run command: {e}")
                self.send({"success": False, "error": str(e)})

    def wg_exists(self, info: dict) -> dict:
        try:
            peer_json = info["peer"]
            peer = PeerInfo.model_validate_json(peer_json)
            wg_if = f"wg{peer.wgid}"
            sp = subprocess.run(["/sbin/ifconfig", wg_if], capture_output=True)
            return {"success": not sp.returncode}
        except Exception as e:
            logger.error(f"Failed to check if interface exists: {e}")
            return {"success": False, "error": str(e)}

    def wg_create(self, info: dict) -> dict:
        try:
            peer_json = info["peer"]
            peer = PeerInfo.model_validate_json(peer_json)
            logger.debug("Creating peer: %s", peer)
            peer.dn42_validate()
            wg_if = f"wg{peer['wgid']}"
            sp = subprocess.run(["/sbin/ifconfig", f"{wg_if}"], capture_output=True)
            if not sp.returncode:
                logger.error(f"Interface {wg_if} already exists")
                return {"success": False, "error": "Interface already exists"}
            wg_file = f"/etc/wireguard/wg{peer['wgid']}.conf"
            wg_data = hostname_wg.render(peer=peer)
            with open(wg_file, "w") as f:
                f.write(wg_data)
            sp = subprocess.run(
                ["/bin/sh", "/etc/netstart", f"{wg_if}"], capture_output=True
            )
            if sp.returncode:
                logger.error(
                    f"Failed to create interface {wg_if}: {sp.stderr.decode()}"
                )
                logger.debug(f"Debug output: {sp.stdout.decode()}")
                return {"success": False, "error": "Failed to create interface"}
        except HTTPException as e:
            return {"success": False, "error": e.detail}
        except Exception as e:
            logger.error(f"Failed to create peer: {e}")
            return {"success": False, "error": str(e)}
        return {"success": True}

    def wg_delete(self, info: dict) -> dict:
        try:
            peer_json = info["peer"]
            peer = PeerInfo.model_validate_json(peer_json)
            logger.debug("Deleting peer: %s", peer)
            peer.dn42_validate()
            wg_file = f"/etc/wireguard/wg{peer['wgid']}.conf"
            if os.path.isfile(wg_file):
                logger.debug(f"Deleting wireguard config file {wg_file}")
                os.unlink(wg_file)
            else:
                logger.warning(f"Wireguard hostname file {wg_file} does not exist")
            wg_if = f"wg{peer['wgid']}"
            sp = subprocess.run(["/sbin/ifconfig", f"{wg_if}"], capture_output=True)
            if not sp.returncode:
                sp = subprocess.run(
                    ["/sbin/ifconfig", f"{wg_if}", "destroy"], capture_output=True
                )
                if sp.returncode:
                    logger.debug(
                        f"Failed to destroy interface {wg_if}: {sp.stderr.decode()}"
                    )
                    logger.debug(f"Debug output: {sp.stdout.decode()}")
                    return {"success": False, "error": "Failed to destroy interface"}
            else:
                logger.warning(f"Interface {wg_if} does not exist")
        except HTTPException as e:
            return {"success": False, "error": e.detail}
        except Exception as e:
            logger.error(f"Failed to delete peer: {e}")
            return {"success": False, "error": str(e)}
        return {"success": True}

    def bgp_update(self, info: dict) -> dict:
        try:
            peers_json = info["peers"]
            peers = [PeerInfo.model_validate_json(peer) for peer in peers_json]
            for peer in peers:
                peer.dn42_validate()
            bgpd_file = "/etc/bgpd.conf"
            bgpd_tmp_file = "/tmp/bgpd.conf"
            bgpd_data = bgpd_conf.render(peers=peers)
            # write to temp file first
            with open(bgpd_tmp_file, "w") as f:
                f.write(bgpd_data)
            # test the config
            sp = subprocess.run(
                ["/usr/sbin/bgpd", "-f", "-n", f"{bgpd_tmp_file}"], capture_output=True
            )
            if sp.returncode:
                logger.error(f"Failed to test bgpd config: {sp.stderr.decode()}")
                os.unlink(bgpd_tmp_file)
                return {"success": False, "error": "Failed to test bgpd config"}
            # move the temp file to the real file
            os.rename(bgpd_tmp_file, bgpd_file)
            # reload bgpd
            sp = subprocess.run(
                ["/usr/sbin/rcctl", "reload", "bgpd"], capture_output=True
            )
            if sp.returncode:
                logger.error(f"Failed to reload bgpd: {sp.stderr.decode()}")
                return {"success": False, "error": "Failed to reload bgpd"}
        except HTTPException as e:
            return {"success": False, "error": e.detail}
        except Exception as e:
            return {"success": False, "error": str(e)}
        return {"success": True}
