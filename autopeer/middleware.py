import base64
import json
import subprocess
import tempfile
from functools import partial
from os import system

import gnupg
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import cache, logger


class GPGMiddleware:
    """
    Middleware to verfify the body of the request using GPG.
    If there is no body, the request is passed through.
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
        logger.debug(f"Body: {body}")

        try:
            jbody = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Body is not a valid JSON")

        # check that request has a valid ASN
        if not "ASN" in jbody:
            raise HTTPException(status_code=400, detail="ASN not found in body")
        ASN = jbody["ASN"]
        if not isinstance(ASN, int):
            raise HTTPException(status_code=400, detail="ASN is not an integer")
        logger.debug(f"ASN: {ASN}")

        # check that request has a signature header
        logger.debug(f"headers: {request.headers}")

        logger.debug("Checking for signature header")
        signature_raw = request.headers.get("X-DN42-Signature")
        if signature_raw is None:
            raise HTTPException(
                status_code=400, detail="X-DN42-Signature header not found"
            )
        logger.debug(f"Signature raw: {signature_raw}")
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
                logger.debug(f"Verified: {verified.valid}")
                if not verified.valid:
                    raise HTTPException(
                        status_code=400, detail="Signature verification failed"
                    )
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error verifying signature: {e}"
            )

        return message


class TokenMiddleware:
    """
    Middleware to verify that the token of the request is valid.
    If there is no body, the request is passed through.
    """

    def __init__(self, app: ASGIApp, gpg: gnupg.GPG = None) -> None:
        self.app = app
        self.gpg = gnupg.GPG() if gpg is None else gpg

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        await self.app(scope, partial(self.verify_token, scope, receive), send)

    async def verify_token(self, scope: Scope, receive: Receive) -> bytes:
        logger.debug("Verifying token")

        request = Request(scope)

        message: Message = await receive()
        assert message["type"] == "http.request"

        body: bytes = message["body"]
        if not body:
            return message
        logger.debug(f"Body: {body}")

        try:
            jbody = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Body is not a valid JSON")

        # check that request has a valid ASN
        if not "ASN" in jbody:
            raise HTTPException(status_code=400, detail="ASN not found in body")
        ASN = jbody["ASN"]
        if not isinstance(ASN, int):
            raise HTTPException(status_code=400, detail="ASN is not an integer")
        logger.debug(f"ASN: {ASN}")

        # check that request has a token header
        if not "token" in jbody:
            raise HTTPException(status_code=400, detail="Token not found in body")
        token = jbody["token"]
        if not isinstance(token, str):
            raise HTTPException(status_code=400, detail="Token is not a string")
        logger.debug(f"Token: {token}")

        # check that token is valid
        try:
            if cache.get(ASN) != token:
                raise HTTPException(status_code=401, detail="Token is invalid")
            cache.pop(ASN)
            logger.debug("ASN {ASN} token cleared")
        except KeyError:
            raise HTTPException(status_code=401, detail="ASN is not logged in")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error verifying token: {e}")

        return message
