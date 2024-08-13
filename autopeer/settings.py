import os
import sqlalchemy as db

from sqlalchemy import String
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase

from .logger import logger
from .database import migrations

class Base(DeclarativeBase):
    pass

class Peer(Base):
    __tablename__ = "peers"

    ASN: Mapped[int] = mapped_column("ASN", primary_key=True)

    WG_PORT: Mapped[int] = mapped_column("WG_PORT", nullable=False, unique=True)
    WG_PRIVKEY: Mapped[str] = mapped_column("WG_PRIVKEY", String(60), nullable=False, unique=True)
    WG_PSK: Mapped[str] = mapped_column("WG_PSK", String(60), nullable=False, unique=True)

    LOCAL_IP6: Mapped[str] = mapped_column("LOCAL_IP6", nullable=False, unique=True)
    LOCAL_IP4: Mapped[str] = mapped_column("LOCAL_IP4", nullable=False, unique=True)

    PEER_IP6: Mapped[str] = mapped_column("PEER_IP6", nullable=False, unique=True)
    PEER_IP4: Mapped[str] = mapped_column("PEER_IP4", nullable=False, unique=True)



class Settings:
    def __init__(self):
        self.initialized = False

    def initialize(self, config: dict):
        self.initialized = True

        self.registry = config.get("registry", self.registry)
        self.database = os.path.join(config.get("database", self.database), "peers.db")
        self.db_engine = db.create_engine(f"sqlite+pysqlite:///{self.database}")
        # self.conn = self.db_engine.connect()

    def get_version(self):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        self.connect()
        version = self.conn.execute("PRAGMA user_version").fetchone()[0]
        return version

    def set_version(self, version: int):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        self.connect()
        self.conn.execute(f"PRAGMA user_version = {version}")
        self.conn.commit()

    def migrate(self):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        self.connect()
        version = 0 #self.get_version()
        for idx, migration in enumerate(migrations):
            migration_id = idx + 1
            if migration_id <= version:
                continue
            logger.debug(f"Executing migration: {migration_id}")
            # self.conn.executescript(migration)
            # self.set_version(migration_id)

    def connect(self):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")
        # self.conn = self.db_engine.connect()
        return
