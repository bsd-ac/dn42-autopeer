import base64
import ipaddress
import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import cache, max_bytes, models, schemas, settings, sp
from .database import SessionLocal
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
    rsp_json = pm_sock.recv(rsp_len)
    try:
        rsp = json.loads(rsp_json)
        if "success" not in rsp:
            logger.critical(f"Invalid response: {rsp}")
            return {"success": False, "error": "Invalid response from peer manager"}
        return rsp
    except json.JSONDecodeError:
        logger.critical(f"Invalid response: {rsp_json}")
        return {"success": False, "error": "Invalid response from peer manager"}
    except Exception as e:
        logger.error(f"Failed to decode response: {e}")
        return {"success": False, "error": str(e)}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app_login.post("/")
async def autopeer_login(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Login to the autopeering service.
    Creates a new session token that is valid for one minute.
    """
    token = uuid.uuid4()
    cache[peer_info.ASN] = f"{token}"
    return {"token": f"{token}"}


@app_peer.post("/info")
async def autopeer_get(peer_info: schemas.PeerInfo, session: Session = Depends(get_db)):
    """
    Get peering information for given ASN.
    """
    peer = (
        session.query(models.PeerInfo)
        .filter(models.PeerInfo.ASN == peer_info.ASN)
        .first()
    )
    logger.debug(f"Peer info: {peer}")
    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.post("/create")
async def autopeer_create(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Create or update a peering session with the given ASN.
    """
    # validate that peer information is valid

    peer_info.dn42_validate()

    jinfo = {"command": "create", "peer_info": peer_info.model_dump()}
    pm_send(jinfo)
    resp = pm_recv()

    logger.debug(f"Received response: {resp}")

    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app_peer.delete("/delete")
async def autopeer_delete(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
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
        raise HTTPException(
            status_code=500,
            detail=f'Error deleting peer: {resp.get("message", "unknown error")}',
        )
    return {"success": True, "message": f"ASN {peer_info.ASN} deleted"}
