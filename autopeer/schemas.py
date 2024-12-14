import base64
import ipaddress
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel, model_validator, root_validator

from autopeer import LL_SUBNET4, LL_SUBNET6, DN42_SUBNET4, DN42_SUBNET6


def ip_validate(ip: str, network: ipaddress.IPv4Network):
    try:
        ip = ipaddress.ip_address(ip)
        if not ip in network:
            raise ValueError
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"IP address {ip} is not in the correct subnet {network}",
        )


class PeerASN(BaseModel):
    ASN: int

class PeerInfo(BaseModel):
    ASN: int
    description: Optional[str] = None
    peer_ip: Optional[str] = None
    peer_port: Optional[int] = None
    peer_pubkey: Optional[str] = None
    peer_psk: Optional[str] = None

    peer_ll_ip6: Optional[str] = None
    peer_ll_ip4: Optional[str] = None

    suggest_ll_ip6: Optional[str] = None
    suggest_ll_ip4: Optional[str] = None

    dn42_ip6: Optional[str] = None
    dn42_ip4: Optional[str] = None

    use_ll_ip6: bool = False
    use_ll_ip4: bool = False

    mp_bgp: bool = False
    extended_next_hop: bool = False


    @model_validator(mode="after")
    def dn42_validate(self):
        if not self.description:
            self.description = f"Peer_{self.ASN}"

        if self.peer_port:
            if self.peer_port < 0 or self.peer_port > 65535:
                raise HTTPException(
                    status_code=400, detail="Peer port is not a valid port number"
                )

        # check that all peer ip are valid IPv4/IPv6 address
        if self.use_ll_ip4:
            if not self.peer_ll_ip4:
                raise HTTPException(
                    status_code=400,
                    detail="LinkLocal IPv4 address not found in body",
                )
        elif not self.dn42_ip4:
            raise HTTPException(
                status_code=400, detail="DN42 IPv4 address not found in body"
            )
        if self.use_ll_ip6:
            if not self.peer_ll_ip6:
                raise HTTPException(
                    status_code=400,
                    detail="LinkLocal IPv6 address not found in body",
                )
        elif not self.dn42_ip6:
            raise HTTPException(
                status_code=400, detail="DN42 IPv6 address not found in body"
            )
        if self.peer_ip:
            try:
                ipaddress.ip_address(self.peer_ip)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"IP address {self.peer_ip} is not a valid IP address",
                )
        for ip4 in [self.peer_ll_ip4, self.suggest_ll_ip4]:
            if ip4:
                ip_validate(ip4, LL_SUBNET4)
        for ip6 in [self.peer_ll_ip6, self.suggest_ll_ip6]:
            if ip6:
                ip_validate(ip6, LL_SUBNET6)
        if self.dn42_ip4:
            ip_validate(self.dn42_ip4, DN42_SUBNET4)
        if self.dn42_ip6:
            ip_validate(self.dn42_ip6, DN42_SUBNET6)

        if not self.peer_pubkey:
            raise HTTPException(
                status_code=400, detail="Peer public key not found in body"
            )
        try:
            pubkey_bytes = base64.b64decode(self.peer_pubkey)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Public key is not a valid base64: {e}"
            )
        if self.peer_psk:
            try:
                psk_bytes = base64.b64decode(self.peer_psk)
            except Exception as e:
                raise HTTPException(
                    status_code=400, detail=f"Pre-shared key is not a valid base64: {e}"
                )
