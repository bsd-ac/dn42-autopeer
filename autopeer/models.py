from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column

from autopeer import WG_KEYLEN

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
