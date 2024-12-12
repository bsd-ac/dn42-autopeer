import os

import sqlalchemy as db
from sqlalchemy.orm import sessionmaker

from autopeer.logger import logger


class Settings:
    def __init__(self):
        self._initialized = False

    def initialize(self, config: dict):
        self._initialized = True

        self._registry = config.get("registry")
        self._registry_url = config.get("registry_url")
        self._database = os.path.join(config.get("db_dir"), "peers.db")
        self._db_engine = db.create_engine(f"sqlite:///{self.database}")
        self._session = sessionmaker(
            autocommit=False, autoflush=False, bind=self.db_engine
        )

    @property
    def registry(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._registry
    
    @property
    def registry_url(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._registry_url
    
    @property
    def db_dir(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._db_dir
    
    @property
    def database(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._database
    
    @property
    def db_engine(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._db_engine
    
    @property
    def session(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._session
