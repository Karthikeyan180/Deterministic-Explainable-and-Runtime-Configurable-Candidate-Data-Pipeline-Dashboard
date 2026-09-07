"""
Explainable Provenance & Confidence Scoring Module
Calculates field-level and profile-level confidence scores with transparent explanations.
"""

from typing import Dict, Any, List
from src.models import CanonicalProfile, FieldValue


class ConfidenceScorer:
    """Computes explainable confidence scores for individual fields and canonical profiles."""

    def __init__(self, field_mapper):
        self.field_mapper = field_mapper

    def compute_field_confidence(
        self,
        field_name: str,
        value: Any,
        source_id: str,
        transformation_rules: List[str]
    ) -> float:
        """
        Calculates field confidence score (0.0 - 1.0) based on source authority and normalization quality.
        """
        if value is None:
            return 0.0

        # Base confidence from source priority
        base_confidence = self.field_mapper.get_source_priority(source_id)

        # Rule penalties or boosts
        penalty = 0.0
        boost = 0.0

        if "failed_syntax_check" in transformation_rules:
            penalty += 0.40
        if "no_digits_found" in transformation_rules:
            penalty += 0.50
        if "failed_numeric_extraction" in transformation_rules:
            penalty += 0.50
        if "extracted_first_numeric_token" in transformation_rules:
            penalty += 0.15
        if "validated_email_pattern" in transformation_rules:
            boost += 0.05
        if "mapped_skill" in transformation_rules:
            boost += 0.05

        confidence = max(0.1, min(1.0, base_confidence - penalty + boost))
        return round(confidence, 4)

    def compute_overall_profile_confidence(self, profile: CanonicalProfile) -> float:
        """
        Computes aggregate profile confidence score based on field completeness and individual field confidences.
        """
        weights = {
            "name": 0.25,
            "email": 0.25,
            "phone": 0.15,
            "skills": 0.15,
            "experience_years": 0.10,
            "education": 0.05,
            "location": 0.05
        }

        total_weight = 0.0
        weighted_sum = 0.0

        for field, weight in weights.items():
            fv: FieldValue = getattr(profile, field, None)
            if fv is not None and fv.value is not None:
                weighted_sum += fv.confidence * weight
                total_weight += weight
            else:
                total_weight += weight  # Unfilled fields contribute 0.0

        # Penalty for active unresolved conflicts
        conflict_penalty = 0.05 * len(profile.conflicts)

        overall = (weighted_sum / total_weight) - conflict_penalty if total_weight > 0 else 0.0
        return round(max(0.0, min(1.0, overall)), 4)
