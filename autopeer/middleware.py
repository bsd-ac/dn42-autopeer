import base64
import email.utils
import json
import subprocess
import tempfile
from functools import partial
from os import system

import gnupg
from fastapi import HTTPException
from starlette.requests import Request
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from . import cache, settings
from .logger import logger
from .settings import Settings
from .utils import DN42


class GPGMiddleware:
    """
    Middleware to verfify the body of the request using GPG.
    If there is no body, the request is passed through.
    """

    def __init__(
        self, app: ASGIApp, gpg: gnupg.GPG = None, settings: Settings = None
    ) -> None:
        self.app = app
        self.gpg = gnupg.GPG() if gpg is None else gpg
        self.settings = settings

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

        # get the email of the ASN
        try:
            mail = DN42.email(self.settings.registry, ASN)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error getting email: {e}")
        if not mail:
            raise HTTPException(status_code=400, detail="ASN not found")
        logger.debug(f"Email: {mail}")

        try:
            pgp_fingerprint = DN42.pgp_fingerprint(self.settings.registry, ASN)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Error getting PGP fingerprint: {e}"
            )
        if not pgp_fingerprint:
            raise HTTPException(status_code=400, detail="PGP fingerprint not found")
        logger.debug(f"PGP fingerprint: {pgp_fingerprint}")

        # get the public key of the ASN
        # only searches for the key using WKD and local keyring
        logger.debug("Getting public key")
        sp = subprocess.run(["gpg", "--locate-keys", mail])
        if sp.returncode != 0:
            logger.warning(f"Error getting public key for: {mail}")

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
                if len(verified.sig_info) > 1:
                    raise HTTPException(
                        status_code=400, detail="More than one signature found"
                    )
                logger.debug(f"Verified: {verified.sig_info}")
                for sig, info in verified.sig_info.items():
                    user = info["username"]
                    try:
                        user_info = email.utils.parseaddr(user)
                    except Exception as e:
                        logger.debug(f"Error parsing email: {e}")
                        raise HTTPException(
                            status_code=400, detail="Error parsing email"
                        )
                    logger.debug(f"Signature by: {user_info}")
                    if user_info[1] != mail:
                        raise HTTPException(
                            status_code=401, detail="Signature by wrong user"
                        )
                    sig_fingerprint = info["pubkey_fingerprint"]
                    logger.debug(f"Signature fingerprint: {sig_fingerprint}")
                    if sig_fingerprint != pgp_fingerprint:
                        raise HTTPException(
                            status_code=401, detail="PGP fingerprint mismatch"
                        )
                    logger.debug("Signature verified")

        except HTTPException:
            raise
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
            if cache[ASN] != token:
                raise HTTPException(status_code=401, detail="Token is invalid")
        except KeyError:
            raise HTTPException(status_code=401, detail="ASN is not logged in")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error verifying token: {e}")

        return message
