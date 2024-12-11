import os

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

from .logger import logger


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
        self.session_local = sessionmaker(
            autocommit=False, autoflush=False, bind=self.db_engine
        )
