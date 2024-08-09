import base64
from functools import partial
import json
import tempfile
from fastapi import HTTPException
from starlette.requests import Request
import gnupg

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import logger

class GPGMiddleware():
    """
    Middleware to verfify the body of the request using GPG.
    """
    def __init__(self, app: ASGIApp, gpg: gnupg.GPG = None) -> None:
        self.app = app
        self.gpg = gnupg.GPG() if gpg is None else gpg

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, partial(self.verify_body, scope, receive), send)

    async def verify_body(self, scope: Scope, receive: Receive) -> bytes:
        logger.debug("Verifying body")

        message : Message = await receive()
        assert message["type"] == "http.request"

        request = Request(scope)
        logger.debug(f"headers: {request.headers}")

        # check that request has a valid ASN
        logger.debug("Checking for ASN header")
        peer_asn_raw = request.headers.get("X-DN42-ASN")
        if peer_asn_raw is None:
            raise HTTPException(status_code=400, detail="X-DN42-ASN header not found")
        try:
            peer_asn = int(peer_asn_raw)
        except ValueError:
            raise HTTPException(status_code=400, detail="X-DN42-ASN header is not an integer")

        logger.debug(f"ASN: {peer_asn}")

        # check that request has a signature header
        logger.debug("Checking for signature header")
        signature_raw = request.headers.get("X-DN42-Signature")
        if signature_raw is None:
            raise HTTPException(status_code=400, detail="X-DN42-Signature header not found")
        try:
            signature = base64.b64decode(signature_raw)
        except Exception:
            raise HTTPException(status_code=400, detail="X-DN42-Signature header is not a valid base64 string")
        logger.debug(f"Signature: {signature}")

        # get GPG key of the ASN
        body : bytes = message["body"]
        try:
            with tempfile.NamedTemporaryFile() as tmpfile:
                tmppath = tmpfile.name
                tmpfile.write(signature)
                tmpfile.flush()
                verified = self.gpg.verify_data(tmppath, body)
                if not verified.valid:
                    raise HTTPException(status_code=400, detail="Signature verification failed")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error verifying signature: {e}")
        logger.debug(f"Verified: {verified.valid}")

        body = message["body"]
        jbody = json.loads(body)
        jbody["peer_asn"] = peer_asn
        message["body"] = json.dumps(jbody).encode()

        logger.debug(f"message body: {message['body']}")

        return message

