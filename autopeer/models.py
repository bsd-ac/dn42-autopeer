from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

from autopeer import DN42_SUBNET4, DN42_SUBNET6, WG_KEYLEN, settings

Base = declarative_base()


class PeerInfoDB(Base):
    __tablename__ = "peerinfo"

    ASN: Mapped[int] = mapped_column("ASN", primary_key=True)

    description: Mapped[str] = mapped_column(
        "DESCRIPTION", String(WG_KEYLEN), nullable=False
    )

    wg_id: Mapped[int] = mapped_column("WG_ID", nullable=False, unique=True)
    wg_privkey: Mapped[str] = mapped_column(
        "WG_PRIVKEY", String(WG_KEYLEN), nullable=False, unique=True
    )
    wg_port: Mapped[int] = mapped_column("WG_PORT", nullable=False, unique=True)

    peer_ip: Mapped[str] = mapped_column("PEER_IP", nullable=True, unique=True)
    peer_port: Mapped[int] = mapped_column("PEER_PORT", nullable=True)
    peer_pubkey: Mapped[str] = mapped_column(
        "PEER_PUBKEY", String(WG_KEYLEN), nullable=False, unique=True
    )
    peer_psk: Mapped[str] = mapped_column(
        "PEER_PSK", String(WG_KEYLEN), nullable=True, unique=True
    )

    peer_ll_ip4: Mapped[str] = mapped_column("PEER_LL_IP4", nullable=True, unique=True)
    peer_ll_ip6: Mapped[str] = mapped_column("PEER_LL_IP6", nullable=True, unique=True)

    dn42_ip4: Mapped[str] = mapped_column("DN42_IP4", nullable=True, unique=True)
    dn42_ip6: Mapped[str] = mapped_column("DN42_IP6", nullable=True, unique=True)

    our_ll_ip4: Mapped[str] = mapped_column("OUR_LL_IP4", nullable=False, unique=True)
    our_ll_ip6: Mapped[str] = mapped_column("OUR_LL_IP6", nullable=False, unique=True)

    use_ll_ip4: Mapped[bool] = mapped_column("USE_LL_IP4", nullable=False)
    use_ll_ip6: Mapped[bool] = mapped_column("USE_LL_IP6", nullable=False)

    mp_bgp: Mapped[bool] = mapped_column("MP_BGP", nullable=False)
    extended_next_hop: Mapped[bool] = mapped_column("EXTENDED_NEXT_HOP", nullable=False)

    def sanitize(self) -> dict:
        return {
            "ASN": self.ASN,
            "PEER_IP": self.peer_ip,
            "PEER_PORT": self.peer_port,
            "PEER_PUBKEY": self.peer_pubkey,
            "PEER_PSK": self.peer_psk,
            "PEER_LL_IP4": self.peer_ll_ip4,
            "PEER_LL_IP6": self.peer_ll_ip6,
            "PEER_DN42_IP4": self.dn42_ip4,
            "PEER_DN42_IP6": self.dn42_ip6,
            "LINKLOCAL_IP4": self.our_ll_ip4,
            "LINKLOCAL_IP6": self.our_ll_ip6,
        }

    def wg_info(self) -> dict:
        model_info = {
            "ASN": self.ASN,
            "description": self.description,
            "wg_id": self.wg_id,
            "wg_rdomain": settings.wg_rdomain,
            "wg_interface": settings.wg_base_interface + self.wg_id,
            "wg_mtu": settings.wg_mtu,
            "wg_privkey": self.wg_privkey,
            "wg_port": self.wg_port,
            "peer_ip": self.peer_ip,
            "peer_port": self.peer_port,
            "peer_pubkey": self.peer_pubkey,
            "peer_psk": self.peer_psk,
            "peer_ll_ip4": (
                self.peer_ll_ip4
                if self.use_ll_ip4
                else self.dn42_ip4
            ),
            "peer_ll_ip6": (
                self.peer_ll_ip6
                if self.use_ll_ip6
                else self.dn42_ip6
            ),
            "our_ll_ip4": self.our_ll_ip4,
            "our_ll_ip6": self.our_ll_ip6,
            "dn42_netspace4": f"{DN42_SUBNET4}",
            "dn42_netspace6": f"{DN42_SUBNET6}",
        }
        model_info = {k: v for k, v in model_info.items() if v is not None}
        return model_info

    def bgp_info(self) -> dict:
        model_info =  {
            "ASN": self.ASN,
            "description": self.description,
            "wg_id": self.wg_id,
            "wg_interface": settings.wg_base_interface + self.wg_id,
            "peer_ll_ip4": self.peer_ll_ip4,
            "peer_ll_ip6": self.peer_ll_ip6,
            "our_ll_ip4": self.our_ll_ip4,
            "our_ll_ip6": self.our_ll_ip6,
            "dn42_ip4": self.dn42_ip4,
            "dn42_ip6": self.dn42_ip6,
            "use_ll_ip4": self.use_ll_ip4,
            "use_ll_ip6": self.use_ll_ip6,
        }
        model_info = {k: v for k, v in model_info.items() if v is not None}
        return model_info
