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
        self._ADMIN_ASN = config.get("ADMIN_ASN")
        self._router_ip4 = config.get("router_ip4")
        self._router_ip6 = config.get("router_ip6")
        self._wg_base_port = config.get("wg_base_port", 2100)
        self._wg_base_interface = config.get("wg_base_interface", 100)
        self._wg_rdomain = config.get("wg_rdomain", 42)
        self._wg_mtu = config.get("wg_mtu", 1420)
        self._gpg_options = config.get("gpg_options", [])
        self._session = sessionmaker(
            autocommit=False, autoflush=False, bind=self.db_engine
        )

    @property
    def ADMIN_ASN(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._ADMIN_ASN

    @property
    def wg_rdomain(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._wg_rdomain

    @property
    def wg_mtu(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._wg_mtu

    @property
    def wg_base_interface(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._wg_base_interface

    @property
    def wg_base_port(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._wg_base_port

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

    @property
    def router_ip4(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._router_ip4

    @property
    def router_ip6(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._router_ip6

    @property
    def gpg_options(self):
        if not self._initialized:
            raise ValueError("Settings not initialized")
        return self._gpg_options
