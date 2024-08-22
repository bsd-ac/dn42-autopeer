import os

import sqlalchemy as db
from sqlalchemy import String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from . import models
from .database import SessionLocal
from .logger import logger
from .migrations import migrations


class Settings:
    def __init__(self):
        self.initialized = False
        self.registry = "/var/db/dn42/registry"
        self.db_dir = "/var/db/dn42/db"

    def initialize(self, config: dict):
        self.initialized = True

        self.registry = config.get("registry", self.registry)
        self.database = os.path.join(config.get("db_dir", self.db_dir), "peers.db")
        self.db_engine = db.create_engine(f"sqlite:///{self.database}")
        models.Base.metadata.create_all(bind=self.db_engine)

    def get_version(self):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        with SessionLocal() as session:
            version = session.execute(text("PRAGMA user_version;")).fetchone()[0]
            session.commit()
            return version

    def set_version(self, version: int):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        with SessionLocal() as session:
            session.execute(text(f"PRAGMA user_version = {version};"))
            session.commit()

    def migrate(self):
        if not self.initialized:
            raise RuntimeError("Settings not initialized")

        version = self.get_version()
        logger.debug(f"Current version: {version}")
        for idx, migration in enumerate(migrations):
            migration_id = idx + 1
            if migration_id <= version:
                continue
            logger.debug(f"Executing migration: {migration_id}")

            with SessionLocal() as session:
                for statement in migration:
                    session.execute(text(statement))
                session.commit()
            self.set_version(migration_id)
