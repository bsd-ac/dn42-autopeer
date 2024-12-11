import base64
import ipaddress
import json
import os
import socket
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import Depends, FastAPI, HTTPException
from git import Repo
from pydantic import BaseModel
from sqlalchemy.orm import Session

from . import cache, max_bytes, models, schemas, settings, sp
from .logger import logger
from .middleware import GPGMiddleware, TokenMiddleware

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    yield
    scheduler.shutdown()

@scheduler.scheduled_job("interval", minutes=5)
def git_update():
    logger.info("Updating registry")
    if not os.path.isdir(settings.registry):
        logger.debug(f"Registry directory not found: {settings.registry}")
        Repo.clone_from(url=settings.registry_url, to_path=settings.registry)
        return
    repo = Repo(settings.registry)
    repo.remotes.origin.pull()
    logger.debug("Registry updated")

app = FastAPI(lifespan=lifespan)
app.add_middleware(GPGMiddleware, settings=settings)
app.add_middleware(TokenMiddleware, check_paths=["/create", "/delete", "/info"])

app.state.sock = sp[1]


def pm_send(pm_sock: socket.socket, cmd: dict):
    cmd_bytes = json.dumps(cmd).encode()
    cmd_len = len(cmd_bytes).to_bytes(max_bytes)
    pm_sock.send(cmd_len)
    pm_sock.send(cmd_bytes)


def pm_recv(pm_sock: socket.socket) -> dict:
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
    session = settings.session
    db = session()
    try:
        yield db
    finally:
        db.close()


@app.post("/login")
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


@app.post("/info")
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


@app.post("/create")
async def autopeer_create(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Create or update a peering session with the given ASN.
    """
    # validate that peer information is valid

    peer_info.dn42_validate()

    jinfo = {"command": "create", "peer_info": peer_info.model_dump()}
    pm_send(app.state.sock, jinfo)
    resp = pm_recv(app.state.sock)

    logger.debug(f"Received response: {resp}")

    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app.delete("/delete")
async def autopeer_delete(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Delete peering session with the given ASN.
    """
    logger.debug(f"Peer info: {peer_info}")
    jinfo = {"command": "delete", "ASN": peer_info.ASN}
    pm_send(app.state.sock, jinfo)
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
