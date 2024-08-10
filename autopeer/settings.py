class Settings:
    def __init__(self, registry: str = None):
        self.registry = registry or "/etc/dn42/registry"

    def update(self, config: dict):
        self.registry = config.get("registry", self.registry)
