import base64
import ipaddress
import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from . import cache, max_bytes, settings, sp
from .logger import logger
from .middleware import GPGMiddleware, TokenMiddleware


app_login = FastAPI()
app_login.add_middleware(GPGMiddleware, settings=settings)

app_peer = FastAPI()
app_peer.add_middleware(GPGMiddleware, settings=settings)
app_peer.add_middleware(TokenMiddleware)

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("interval", seconds=5)
async def clear_cache():
    logger.debug("Clearing cache")
    cache.clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.migrate()
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/login", app_login)
app.mount("/peer", app_peer)


class PeerInfo(BaseModel):
    ASN: int
    peer_ip: Optional[str] = None
    peer_port: Optional[int] = None
    peer_pubkey: Optional[str] = None

    ll_ip6: Optional[str] = None
    ll_ip4: Optional[str] = None

    dn42_ip6: Optional[str] = None
    dn42_ip4: Optional[str] = None

    def validate(self):
        if not self.peer_port:
            raise HTTPException(status_code=400, detail="Peer port not found in body")
        if self.peer_port < 0 or self.peer_port > 65535:
            raise HTTPException(status_code=400, detail="Peer port is not a valid port number")

        # check that all peer ip are valid IPv4/IPv6 address
        if not self.peer_ip:
            raise HTTPException(status_code=400, detail="Peer IP address not found in body")
        if not self.ll_ip4:
            raise HTTPException(status_code=400, detail="Local IPv4 address not found in body")
        if not self.ll_ip6:
            raise HTTPException(status_code=400, detail="Local IPv6 address not found in body")
        if not self.dn42_ip4:
            raise HTTPException(status_code=400, detail="DN42 IPv4 address not found in body")
        if not self.dn42_ip6:
            raise HTTPException(status_code=400, detail="DN42 IPv6 address not found in body")
        try:
            ipaddress.ip_address(self.peer_ip)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"IP address {self.peer_ip} is not a valid IP address")
        for ip in [self.ll_ip4, self.dn42_ip4]:
            try:
                ip = ipaddress.ip_address(ip)
                if not isinstance(ip, ipaddress.IPv4Address):
                    raise ValueError
            except ValueError:
                raise HTTPException(status_code=400, detail=f"IP address {ip} is not a valid IPv4 address")
        for ip in [self.ll_ip6, self.dn42_ip6]:
            try:
                ip = ipaddress.ip_address(ip)
                if not isinstance(ip, ipaddress.IPv6Address):
                    raise ValueError
            except ValueError:
                raise HTTPException(status_code=400, detail=f"IP address {ip} is not a valid IPv6 address")

        # check if pubkey is valid base64
        if not self.peer_pubkey:
            raise HTTPException(status_code=400, detail="Peer public key not found in body")
        try:
            pubkey_bytes = base64.b64decode(self.peer_pubkey)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Public key is not a valid base64")

pm_sock = sp[1]


def pm_send(cmd: dict):
    cmd_bytes = json.dumps(cmd).encode()
    cmd_len = len(cmd_bytes).to_bytes(max_bytes)
    pm_sock.send(cmd_len)
    pm_sock.send(cmd_bytes)


def pm_recv() -> dict:
    rsp_bytes = pm_sock.recv(max_bytes)
    try:
        rsp_len = int.from_bytes(rsp_bytes)
    except ValueError:
        logger.critical(f"Invalid command length: {rsp_bytes}")
        raise ValueError
    rsp = pm_sock.recv(rsp_len)
    return json.loads(rsp)


@app_login.post("/")
async def autopeer_login(peer_info: PeerInfo):
    """
    Login to the autopeering service.
    Creates a new session token that is valid for one minute.
    """
    token = uuid.uuid4()
    cache[peer_info.ASN] = f"{token}"
    return {"token": f"{token}"}


@app_peer.post("/info")
async def autopeer_get(peer_info: PeerInfo):
    """
    Get peering information for given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.post("/create")
async def autopeer_create(peer_info: PeerInfo):
    """
    Create or update a peering session with the given ASN.
    """
    # validate that peer information is valid

    peer_info.validate()

    jinfo = {"command": "create", "peer_info": peer_info.model_dump()}
    pm_send(jinfo)
    resp = pm_recv()

    logger.debug(f"Received response: {resp}")

    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.delete("/delete")
async def autopeer_delete(peer_info: PeerInfo):
    """
    Delete peering session with the given ASN.
    """
    logger.debug(f"Peer info: {peer_info}")
    jinfo = {"command": "delete", "ASN": peer_info.ASN}
    pm_send(jinfo)
    try:
        resp = pm_recv()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting peer: {e}")
    
    success = resp.get("success", False)
    if not success:
        raise  HTTPException(status_code=500, detail=f'Error deleting peer: {resp.get("message", "unknown error")}')
    return {"success": True, "message": f"ASN {peer_info.ASN} deleted"}
