# enrichers/BaseService.py
import os, json

class BaseService:
    _definition_cache = {}

    def __init__(self, definitions_dir="data/definitions"):
        self.definitions_dir = definitions_dir

    def _load_definition(self, name: str) -> dict:
        """Charge une définition locale avec cache mémoire."""
        if name in BaseService._definition_cache:
            return BaseService._definition_cache[name]

        path = os.path.join(self.definitions_dir, f"{name}.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                BaseService._definition_cache[name] = data
                return data
        return {}

    def _resolve_hash(self, hash_value: int, definition_name: str) -> dict:
        """Retourne la définition correspondant à un hash donné."""
        defs = self._load_definition(definition_name)
        return defs.get(str(hash_value), {})