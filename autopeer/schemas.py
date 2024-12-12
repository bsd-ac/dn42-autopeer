import base64
import ipaddress
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel


DN42_SUBNET4=ipaddress.IPv4Network("172.20.0.0/14")
DN42_SUBNET6=ipaddress.IPv6Network("fd00::/8")

LL_SUBNET4=ipaddress.IPv4Network("169.254.0.0/16")
LL_SUBNET6=ipaddress.IPv4Network("fe80::/10")

class PeerInfo(BaseModel):
    ASN: int
    description: Optional[str] = None
    peer_ip: Optional[str] = None
    peer_port: Optional[int] = None
    peer_pubkey: Optional[str] = None
    peer_psk: Optional[str] = None

    ll_ip6: Optional[str] = None
    ll_ip4: Optional[str] = None

    dn42_ip6: Optional[str] = None
    dn42_ip4: Optional[str] = None

    def dn42_validate(self):
        if not self.description:
            self.description = f"Peer_{self.ASN}"

        if not self.peer_port:
            raise HTTPException(status_code=400, detail="Peer port not found in body")
        if self.peer_port < 0 or self.peer_port > 65535:
            raise HTTPException(
                status_code=400, detail="Peer port is not a valid port number"
            )

        # check that all peer ip are valid IPv4/IPv6 address
        if not self.peer_ip:
            raise HTTPException(
                status_code=400, detail="Peer IP address not found in body"
            )
        if not self.ll_ip4:
            raise HTTPException(
                status_code=400, detail="LinkLocal IPv4 address not found in body"
            )
        if not self.ll_ip6:
            raise HTTPException(
                status_code=400, detail="LinkLocal IPv6 address not found in body"
            )
        if not self.dn42_ip4:
            raise HTTPException(
                status_code=400, detail="DN42 IPv4 address not found in body"
            )
        if not self.dn42_ip6:
            raise HTTPException(
                status_code=400, detail="DN42 IPv6 address not found in body"
            )
        try:
            ipaddress.ip_address(self.peer_ip)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"IP address {self.peer_ip} is not a valid IP address",
            )
        for ip in [self.ll_ip4, self.dn42_ip4]:
            try:
                ip = ipaddress.ip_address(ip)
                if not isinstance(ip, ipaddress.IPv4Address):
                    raise ValueError
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"IP address {ip} is not a valid IPv4 address",
                )
        for ip in [self.ll_ip6, self.dn42_ip6]:
            try:
                ip = ipaddress.ip_address(ip)
                if not isinstance(ip, ipaddress.IPv6Address):
                    raise ValueError
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"IP address {ip} is not a valid IPv6 address",
                )
        if not DN42_SUBNET4.supernet_of(ipaddress.ip_network(self.dn42_ip4)):
            raise HTTPException(
                status_code=400,
                detail=f"DN42 IPv4 address {self.dn42_ip4} is not in the DN42 subnet",
            )
        if not DN42_SUBNET6.supernet_of(ipaddress.ip_network(self.dn42_ip6)):
            raise HTTPException(
                status_code=400,
                detail=f"DN42 IPv6 address {self.dn42_ip6} is not in the DN42 subnet",
            )
        if not LL_SUBNET4.supernet_of(ipaddress.ip_network(self.ll_ip4)):
            raise HTTPException(
                status_code=400,
                detail=f"Local IPv4 address {self.ll_ip4} is not in the link-local subnet",
            )
        if not LL_SUBNET6.supernet_of(ipaddress.ip_network(self.ll_ip6)):
            raise HTTPException(
                status_code=400,
                detail=f"Local IPv6 address {self.ll_ip6} is not in the link-local subnet",
            )

        if not self.peer_pubkey:
            raise HTTPException(
                status_code=400, detail="Peer public key not found in body"
            )
        try:
            pubkey_bytes = base64.b64decode(self.peer_pubkey)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail=f"Public key is not a valid base64"
            )
