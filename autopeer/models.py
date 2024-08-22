from sqlalchemy import String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .database import Base


class PeerInfo(Base):
    __tablename__ = "peers"

    ASN: Mapped[int] = mapped_column("ASN", primary_key=True)
    description: Mapped[str] = mapped_column("DESCRIPTION", String(30), nullable=False)

    peer_ip: Mapped[str] = mapped_column("PEER_IP", nullable=False, unique=True)
    peer_port: Mapped[int] = mapped_column("PEER_PORT", nullable=False, unique=True)
    peer_pubkey: Mapped[str] = mapped_column("PEER_PUBKEY", nullable=False, unique=True)
    peer_psk: Mapped[str] = mapped_column("PEER_PSK", nullable=False, unique=True)

    ll_ip4: Mapped[str] = mapped_column("LL_IP4", nullable=False, unique=True)
    ll_ip6: Mapped[str] = mapped_column("LL_IP6", nullable=False, unique=True)

    dn42_ip4: Mapped[str] = mapped_column("DN42_IP4", nullable=False, unique=True)
    dn42_ip6: Mapped[str] = mapped_column("DN42_IP6", nullable=False, unique=True)
