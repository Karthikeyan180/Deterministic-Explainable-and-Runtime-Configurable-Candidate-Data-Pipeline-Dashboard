"""
Conflict Resolution Module
Resolves conflicting candidate field values from multiple sources using configurable policies.
"""

from typing import List, Dict, Any, Tuple
from src.models import ProvenanceEntry, FieldValue, ConflictRecord


class ConflictResolver:
    """Resolves data conflicts across multiple records belonging to the same candidate."""

    def __init__(self, field_mapper):
        self.field_mapper = field_mapper

    def resolve_field_conflict(
        self,
        field_name: str,
        competing_values: List[Dict[str, Any]],
        strategy: str = "highest_confidence"
    ) -> Tuple[FieldValue, Optional[ConflictRecord]]:
        """
        Resolves competing field values for a specific candidate field.
        competing_values structure:
            [{
                "value": Any,
                "source_id": str,
                "confidence": float,
                "raw_key": str,
                "raw_value": Any,
                "transformation_rules": List[str],
                "timestamp": float
            }, ...]
        """
        if not competing_values:
            return FieldValue(value=None, confidence=0.0), None

        if len(competing_values) == 1:
            item = competing_values[0]
            prov = ProvenanceEntry(
                source_id=item["source_id"],
                raw_key=item["raw_key"],
                raw_value=item["raw_value"],
                transformed_value=item["value"],
                transformation_rules=item["transformation_rules"],
                confidence_score=item["confidence"],
                timestamp=item.get("timestamp", 0.0)
            )
            return FieldValue(value=item["value"], confidence=item["confidence"], provenance=[prov]), None

        # Handle Array fields (e.g. skills) via Array Union
        if field_name == "skills":
            return self._resolve_skills_union(competing_values)

        # Check if all competing values are identical
        distinct_vals = {str(item["value"]) for item in competing_values}
        if len(distinct_vals) == 1:
            # Agreement boost across multiple sources
            item = competing_values[0]
            all_provs = [
                ProvenanceEntry(
                    source_id=it["source_id"],
                    raw_key=it["raw_key"],
                    raw_value=it["raw_value"],
                    transformed_value=it["value"],
                    transformation_rules=it["transformation_rules"],
                    confidence_score=it["confidence"],
                    timestamp=it.get("timestamp", 0.0)
                ) for it in competing_values
            ]
            boosted_confidence = min(1.0, item["confidence"] + 0.05 * (len(competing_values) - 1))
            return FieldValue(value=item["value"], confidence=boosted_confidence, provenance=all_provs), None

        # Conflict exists! Evaluate resolution strategy
        chosen_item = None
        explanation = ""

        if strategy == "source_priority":
            # Pick by source priority weight
            chosen_item = max(competing_values, key=lambda x: self.field_mapper.get_source_priority(x["source_id"]))
            explanation = f"Selected value from highest priority source ({chosen_item['source_id']})"
        elif strategy == "latest_timestamp":
            chosen_item = max(competing_values, key=lambda x: x.get("timestamp", 0.0))
            explanation = f"Selected value from most recent update ({chosen_item['source_id']})"
        else: # Default: highest_confidence
            chosen_item = max(competing_values, key=lambda x: x["confidence"])
            explanation = f"Selected value with highest confidence score ({chosen_item['confidence']:.2f})"

        # Create Provenance list
        all_provs = [
            ProvenanceEntry(
                source_id=it["source_id"],
                raw_key=it["raw_key"],
                raw_value=it["raw_value"],
                transformed_value=it["value"],
                transformation_rules=it["transformation_rules"] + (["selected_in_conflict"] if it == chosen_item else ["rejected_in_conflict"]),
                confidence_score=it["confidence"],
                timestamp=it.get("timestamp", 0.0)
            ) for it in competing_values
        ]

        conflict_record = ConflictRecord(
            field_name=field_name,
            competing_values=[{
                "source_id": it["source_id"],
                "value": it["value"],
                "confidence": it["confidence"]
            } for it in competing_values],
            resolved_value=chosen_item["value"],
            resolution_strategy=strategy,
            explanation=explanation
        )

        return FieldValue(value=chosen_item["value"], confidence=chosen_item["confidence"], provenance=all_provs), conflict_record

    def _resolve_skills_union(self, competing_values: List[Dict[str, Any]]) -> Tuple[FieldValue, Optional[ConflictRecord]]:
        """Merges skill lists across all sources via set union."""
        combined_skills = set()
        all_provs = []
        conf_scores = []

        for item in competing_values:
            skills = item["value"]
            if isinstance(skills, list):
                combined_skills.update(skills)
            elif isinstance(skills, str):
                combined_skills.add(skills)

            conf_scores.append(item["confidence"])
            all_provs.append(
                ProvenanceEntry(
                    source_id=item["source_id"],
                    raw_key=item["raw_key"],
                    raw_value=item["raw_value"],
                    transformed_value=item["value"],
                    transformation_rules=item["transformation_rules"] + ["merged_skills_union"],
                    confidence_score=item["confidence"],
                    timestamp=item.get("timestamp", 0.0)
                )
            )

        merged_list = sorted(list(combined_skills))
        avg_conf = (sum(conf_scores) / len(conf_scores)) if conf_scores else 0.9

        return FieldValue(value=merged_list, confidence=round(avg_conf, 4), provenance=all_provs), None
