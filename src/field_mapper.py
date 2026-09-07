"""
Configurable Field Mapping Engine
Maps heterogeneous input field names to canonical field names using JSON configuration files.
"""

import json
import os
from typing import Dict, Any, List, Optional


class FieldMapper:
    """Configurable mapper that translates incoming field names to canonical schema fields."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self.canonical_fields = []
        self.mappings: Dict[str, List[str]] = {}
        self.reverse_mapping: Dict[str, str] = {}
        self.source_priorities: Dict[str, float] = {}
        self.load_config(config_path)

    def load_config(self, config_path: str):
        """Loads or reloads mapping configuration from JSON file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Field mapping config not found at: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.canonical_fields = data.get("canonical_fields", [])
        self.mappings = data.get("mappings", {})
        self.source_priorities = data.get("source_priorities", {})

        # Build fast lower-case lookup map (raw_key_normalized -> canonical_key)
        self.reverse_mapping = {}
        for canonical_key, aliases in self.mappings.items():
            for alias in aliases:
                norm_alias = self._normalize_key(alias)
                self.reverse_mapping[norm_alias] = canonical_key

    def _normalize_key(self, key: str) -> str:
        """Normalizes field names (lowercasing, replacing spaces/dashes with underscores)."""
        return key.strip().lower().replace(" ", "_").replace("-", "_")

    def map_raw_record(self, raw_data: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Maps raw input data dictionary to canonical field names.
        Returns:
            (mapped_canonical_data, raw_key_provenance_map)
        """
        mapped = {}
        raw_key_map = {}

        for raw_key, raw_value in raw_data.items():
            if raw_value is None or raw_value == "":
                continue

            norm_key = self._normalize_key(raw_key)

            # Check if direct match or alias match
            if norm_key in self.reverse_mapping:
                canonical_key = self.reverse_mapping[norm_key]
                mapped[canonical_key] = raw_value
                raw_key_map[canonical_key] = raw_key
            else:
                # Fuzzy fallback matching for composite keys (e.g., candidate_email_address)
                matched_canonical = self._fuzzy_match_key(norm_key)
                if matched_canonical:
                    mapped[matched_canonical] = raw_value
                    raw_key_map[matched_canonical] = raw_key
                else:
                    # Retain extra unmapped fields under their raw name
                    mapped[raw_key] = raw_value
                    raw_key_map[raw_key] = raw_key

        return mapped, raw_key_map

    def _fuzzy_match_key(self, norm_key: str) -> Optional[str]:
        """Performs substring and key matching for unlisted variants."""
        for canonical_key in self.canonical_fields:
            if canonical_key in norm_key:
                return canonical_key
        return None

    def get_source_priority(self, source_id: str) -> float:
        """Returns the confidence priority multiplier for a given source."""
        source_lower = source_id.lower()
        for key, priority in self.source_priorities.items():
            if key in source_lower:
                return priority
        return self.source_priorities.get("unknown", 0.6)
