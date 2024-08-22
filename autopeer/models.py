from sqlalchemy import String, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

Base = declarative_base()


class PeerInfo(Base):
    __tablename__ = "peerinfo"

    ASN: Mapped[int] = mapped_column("ASN", primary_key=True)
    description: Mapped[str] = mapped_column("DESCRIPTION", String(30), nullable=False)

    peer_ip: Mapped[str] = mapped_column("PEER_IP", nullable=False, unique=True)
    peer_port: Mapped[int] = mapped_column("PEER_PORT", nullable=False)
    peer_pubkey: Mapped[str] = mapped_column(
        "PEER_PUBKEY", String(30), nullable=False, unique=True
    )
    peer_psk: Mapped[str] = mapped_column(
        "PEER_PSK", String(30), nullable=False, unique=True
    )

    ll_ip4: Mapped[str] = mapped_column("LL_IP4", nullable=False, unique=True)
    ll_ip6: Mapped[str] = mapped_column("LL_IP6", nullable=False, unique=True)

    dn42_ip4: Mapped[str] = mapped_column("DN42_IP4", nullable=False, unique=True)
    dn42_ip6: Mapped[str] = mapped_column("DN42_IP6", nullable=False, unique=True)
