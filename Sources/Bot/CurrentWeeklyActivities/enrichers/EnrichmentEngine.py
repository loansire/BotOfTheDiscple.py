# enrichers/EnrichmentEngine.py
from .BaseService import BaseService
from utils.Config import KEY_MAP

class EnrichmentEngine(BaseService):
    def __init__(self, definitions_dir="data/definitions"):
        super().__init__(definitions_dir)

    def enrich_object(self, obj: dict) -> dict:
        """Enrichit un dict en fonction des clés présentes et de KEY_MAP."""
        enriched = obj.copy()

        for key, def_name in KEY_MAP.items():
            if key in obj:
                value = obj[key]

                # Hash simple
                if isinstance(value, int):
                    enriched[key + "_def"] = self._resolve_hash(value, def_name)

                # Liste de hashes
                elif isinstance(value, list) and all(isinstance(v, int) for v in value):
                    enriched[key + "_def"] = [self._resolve_hash(v, def_name) for v in value]

        return enriched
