import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from pydantic import BaseModel

from . import cache, logger, max_bytes, sp
from .middleware import GPGMiddleware, TokenMiddleware


app_login = FastAPI()
app_login.add_middleware(GPGMiddleware)

app_peer = FastAPI()
app_peer.add_middleware(GPGMiddleware)
app_peer.add_middleware(TokenMiddleware)

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("interval", seconds=5)
async def clear_cache():
    logger.debug("Clearing cache")
    cache.clear()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(lifespan=lifespan)
app.mount("/login", app_login)
app.mount("/peer", app_peer)


class PeerInfo(BaseModel):
    ASN: int
    peer_ip: Optional[str] = None
    peer_pubkey: Optional[str] = None
    peer_contact: Optional[str] = None


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
    Create a peering session with the given ASN.
    """
    jinfo = {"ASN": 1234}
    pm_send(jinfo)
    resp = pm_recv()

    logger.debug(f"Received response: {resp}")

    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.put("/update")
async def autopeer_update(peer_info: PeerInfo):
    """
    Update peering information for given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.delete("/delete")
async def autopeer_delete(peer_info: PeerInfo):
    """
    Delete peering session with the given ASN.
    """
    return {"message": f"Autopeering with ASN {peer_info.ASN}"}
