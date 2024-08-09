import base64
import json
import tempfile
from functools import partial

import gnupg
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import logger


class GPGMiddleware:
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

        request = Request(scope)

        message: Message = await receive()
        assert message["type"] == "http.request"

        body: bytes = message["body"]
        if not body:
            return message

        try:
            jbody = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Body is not a valid JSON")

        # check that request has a valid ASN
        if not "peer_asn" in jbody:
            raise HTTPException(status_code=400, detail="peer_asn not found in body")
        peer_asn = jbody["peer_asn"]
        if not isinstance(peer_asn, int):
            raise HTTPException(status_code=400, detail="peer_asn is not an integer")
        logger.debug(f"ASN: {peer_asn}")

        # check that request has a signature header
        logger.debug(f"headers: {request.headers}")

        logger.debug("Checking for signature header")
        signature_raw = request.headers.get("X-DN42-Signature")
        if signature_raw is None:
            raise HTTPException(
                status_code=400, detail="X-DN42-Signature header not found"
            )
        try:
            signature = base64.b64decode(signature_raw)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="X-DN42-Signature header is not a valid base64 string",
            )
        logger.debug(f"Signature: {signature}")

        # get GPG key of the ASN
        try:
            with tempfile.NamedTemporaryFile() as tmpfile:
                tmppath = tmpfile.name
                tmpfile.write(signature)
                tmpfile.flush()
                verified = self.gpg.verify_data(tmppath, body)
                if not verified.valid:
                    raise HTTPException(
                        status_code=400, detail="Signature verification failed"
                    )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error verifying signature: {e}"
            )
        logger.debug(f"Verified: {verified.valid}")

        logger.debug(f"message body: {message['body']}")

        return message
