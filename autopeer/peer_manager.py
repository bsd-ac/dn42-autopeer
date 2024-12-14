import base64
import ipaddress
import json
import os
from pathlib import Path
import socket
import subprocess
from typing import Generator, Optional

from fastapi import HTTPException

from autopeer import max_bytes
from autopeer.logger import logger
from autopeer.schemas import PeerInfo
from autopeer.templates import bgpd_group, bgpd_macros, hostname_wg
from autopeer.utils import mvswap_files


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
            peer = info["peer_info"]
            wg_interface = f"wg{peer['wg_interface']}"
            sp = subprocess.run(["/sbin/ifconfig", f"{wg_interface}"], capture_output=True)
            return {"success": not sp.returncode}
        except Exception as e:
            logger.error(f"Failed to check if interface exists: {e}")
            return {"success": False, "error": str(e)}

    def wg_create(self, info: dict) -> dict:
        try:
            peer = info["peer_info"]
            logger.debug("Creating peer: %s", peer)
            wg_interface = f"wg{peer['wg_interface']}"
            if self.wg_exists(info)["success"]:
                logger.error(f"Interface {wg_interface} already exists")
                return {"success": False, "error": "Interface already exists"}
            wg_file = f"/etc/hostname.{wg_interface}"
            wg_data = hostname_wg.render(**peer)
            with open(wg_file, "w") as f:
                f.write(wg_data)
            sp = subprocess.run(
                ["/bin/sh", "/etc/netstart", f"{wg_interface}"], capture_output=True
            )
            if sp.returncode:
                logger.error(
                    f"Failed to create interface {wg_interface}: {sp.stderr.decode()}"
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
            peer = info["peer_info"]
            logger.debug("Deleting peer: %s", peer)
            wg_interface = f"wg{peer['wg_interface']}"
            wg_file = f"/etc/hostname.{wg_interface}"
            if os.path.isfile(wg_file):
                logger.debug(f"Deleting wireguard config file {wg_file}")
                os.unlink(wg_file)
            else:
                logger.warning(f"Wireguard hostname file {wg_file} does not exist")
            if self.wg_exists(info)["success"]:
                sp = subprocess.run(
                    ["/sbin/ifconfig", f"{wg_interface}", "destroy"], capture_output=True
                )
                if sp.returncode:
                    logger.debug(
                        f"Failed to destroy interface {wg_interface}: {sp.stderr.decode()}"
                    )
                    logger.debug(f"Debug output: {sp.stdout.decode()}")
                    return {"success": False, "error": "Failed to destroy interface"}
        except HTTPException as e:
            return {"success": False, "error": e.detail}
        except Exception as e:
            logger.error(f"Failed to delete peer: {e}")
            return {"success": False, "error": str(e)}
        return {"success": True}

    def bgp_update(self, info: dict) -> dict:
        success = True
        error = None
        try:
            peers = info["peers"] # multiple peers
            logger.debug("Updating BGP: %s", peers)

            bgpd_macros_file = "/etc/bgpd.d/dn42-macros.conf"
            bgpd_macros_file_tmp = "/etc/bgpd.d/dn42-macros.conf.tmp"
            bgpd_group_file = "/etc/bgpd.d/dn42-group.conf"
            bgpd_group_file_tmp = "/etc/bgpd.d/dn42-group.conf.tmp"

            logger.debug("Creating BGP config files")
            if not os.path.isdir("/etc/bgpd.d"):
                os.mkdir("/etc/bgpd.d")

            logger.debug("Ensuring original files exist")
            for f in [bgpd_macros, bgpd_group]:
                Path(f).touch()

            logger.debug("Rendering BGP macros file")
            bgpd_macros_data = bgpd_macros.render(peers=peers)
            logger.debug(f"bgpd_macros_data: {bgpd_macros_data}")
            with open(bgpd_macros_file_tmp, "w") as f:
                f.write(bgpd_macros_data)
            logger.debug("Swapping BGP macros files")
            mvswap_files(bgpd_macros_file, bgpd_macros_file_tmp)

            logger.debug("Rendering BGP group file")
            bgpd_group_data = bgpd_group.render(peers=peers)
            logger.debug(f"bgpd_group_data: {bgpd_group_data}")
            with open(bgpd_group_file_tmp, "w") as f:
                f.write(bgpd_group_data)
            logger.debug("Swapping BGP group files")
            mvswap_files(bgpd_group_file, bgpd_group_file_tmp)

            # test the config
            sp = subprocess.run(
                ["/usr/sbin/rcctl", "configtest", "bgpd"], capture_output=True
            )
            if sp.returncode:
                logger.error(f"Failed to test bgpd config: {sp.stderr.decode()}")
                mvswap_files(bgpd_macros_file, bgpd_macros_file_tmp)
                mvswap_files(bgpd_group_file, bgpd_group_file_tmp)
                raise RuntimeError("Failed to test bgpd config")
            # reload bgpd
            sp = subprocess.run(
                ["/usr/sbin/rcctl", "reload", "bgpd"], capture_output=True
            )
            if sp.returncode:
                logger.error(f"Failed to reload bgpd: {sp.stderr.decode()}")
                raise RuntimeError("Failed to reload bgpd")
        except HTTPException as e:
            success = False
            error = e.detail
        except Exception as e:
            success = False
            error = str(e)
        finally:
            if os.path.isfile(bgpd_macros_file_tmp):
                os.unlink(bgpd_macros_file_tmp)
            if os.path.isfile(bgpd_group_file_tmp):
                os.unlink(bgpd_group_file_tmp)
        
        return {"success": success, "error": error}

