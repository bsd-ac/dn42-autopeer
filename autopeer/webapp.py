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

from autopeer import cache, max_bytes, models, schemas, settings, sp
from autopeer.logger import logger
from autopeer.middleware import GPGMiddleware, TokenMiddleware

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
    peer_info_internal = (
        session.query(models.PeerInfoDB)
        .filter(models.PeerInfoDB.ASN == peer_info.ASN)
        .first()
    )
    if not peer_info_internal:
        return {"message": f"No peer found with ASN {peer_info.ASN}"}
    logger.debug(f"Peer info: {peer_info_internal}")
    peer_info_sanitized = {
        "ASN": peer_info_internal.ASN,
        "PEER_IP": peer_info_internal.peer_ip,
        "PEER_PORT": peer_info_internal.peer_port,
        "PEER_PUBKEY": peer_info_internal.peer_pubkey,
        "PEER_PSK": peer_info_internal.peer_psk,
        "LINKLOCAL_IP4": peer_info_internal.ll_ip4,
        "LINKLOCAL_IP6": peer_info_internal.ll_ip6,
        "DN42_IP4": peer_info_internal.dn42_ip4,
        "DN42_IP6": peer_info_internal.dn42_ip6,
    }
    return {"peer_info": json.dumps(peer_info_sanitized)}


@app.post("/create")
async def autopeer_create(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Create or update a peering session with the given ASN.
    """
    # validate that peer information is valid

    peer_info.dn42_validate()

    # generate new wgid
    # we will use it for wireguard port and interface name
    new_wgid = 1
    max_wgid = session.query(models.PeerInfoDB).order_by(models.PeerInfoDB.wgid.desc()).first()
    if max_wgid:
        new_wgid = max_wgid.wgid + 1

    # generate new wireguard privkey
    wg_privkey = base64.b64encode(os.urandom(32))

    # check if suggested linklocal IPs are already in use
    # try:
    #     if peer_info.suggest_ll_ip4:
    #         our_ll = session.query(models.PeerInfoDB).filter(models.PeerInfoDB.our_ll_ip4 == peer_info.suggest_ll_ip4).first()
    #         if our_ll:
    #             raise RuntimeError
    #         their_ll = session.query(models.PeerInfoDB).filter(models.PeerInfoDB.peer_ll_ip4 == peer_info.suggest_ll_ip4).first()
    #         if their_ll:
    #             raise RuntimeError
    # except RuntimeError:
    #     # generate new linklocal IP
    #     peer_info.suggest_ll_ip4 = 


    # convert peer_info to PeerInfoDB
    peer_info_db = models.PeerInfoDB(
        ASN=peer_info.ASN,
        wgid=new_wgid,
        wg_privkey=wg_privkey,
        description=peer_info.description,
        peer_ip=peer_info.peer_ip,
        peer_port=peer_info.peer_port,
        peer_pubkey=peer_info.peer_pubkey,
        peer_psk=peer_info.peer_psk,
        peer_ll_ip4=peer_info.peer_ll_ip4,
        peer_ll_ip6=peer_info.peer_ll_ip6,
        dn42_ip4=peer_info.dn42_ip4,
        dn42_ip6=peer_info.dn42_ip6,
        our_ll_ip4=peer_info.suggest_ll_ip4,
        our_ll_ip6=peer_info.suggest_ll_ip6,
    )

    # add or update peer info
    session.merge(peer_info_db)
    session.commit()


    # jinfo = {"command": "create", "peer_info": peer_info.model_dump()}
    # pm_send(app.state.sock, jinfo)
    # resp = pm_recv(app.state.sock)

    # logger.debug(f"Received response: {resp}")

    return {"message": f"Autopeering with ASN {peer_info.ASN}"}


@app.delete("/delete")
async def autopeer_delete(
    peer_info: schemas.PeerInfo, session: Session = Depends(get_db)
):
    """
    Delete peering session with the given ASN.
    """
    logger.debug(f"Peer info: {peer_info}")
    # jinfo = {"command": "delete", "ASN": peer_info.ASN}
    # pm_send(app.state.sock, jinfo)
    # try:
    #     resp = pm_recv()
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=f"Error deleting peer: {e}")

    # success = resp.get("success", False)
    # if not success:
    #     raise HTTPException(
    #         status_code=500,
    #         detail=f'Error deleting peer: {resp.get("message", "unknown error")}',
    #     )
    return {"success": True, "message": f"ASN {peer_info.ASN} deleted"}
