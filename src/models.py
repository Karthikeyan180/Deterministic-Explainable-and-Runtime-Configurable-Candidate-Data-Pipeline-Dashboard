"""
Core Data Models for Candidate Data Transformation System
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
import time
import uuid


@dataclass
class RawRecord:
    """Represents an un-normalized raw candidate record ingested from a source."""
    record_id: str
    source_id: str  # e.g., "resume.json", "candidates.csv", "application_form"
    source_type: str  # "json", "csv", "text", "form"
    raw_data: Dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class ProvenanceEntry:
    """Tracks field lineage and history for explainability."""
    source_id: str
    raw_key: str
    raw_value: Any
    transformed_value: Any
    transformation_rules: List[str]
    confidence_score: float
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "raw_key": self.raw_key,
            "raw_value": self.raw_value,
            "transformed_value": self.transformed_value,
            "transformation_rules": self.transformation_rules,
            "confidence_score": round(self.confidence_score, 4),
            "timestamp": self.timestamp
        }


@dataclass
class FieldValue:
    """Represents a canonical candidate field value with provenance and confidence."""
    value: Any
    confidence: float
    provenance: List[ProvenanceEntry] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "confidence": round(self.confidence, 4),
            "provenance": [p.to_dict() for p in self.provenance]
        }


@dataclass
class ConflictRecord:
    """Records conflicting values detected during multi-source merging."""
    field_name: str
    competing_values: List[Dict[str, Any]]
    resolved_value: Any
    resolution_strategy: str
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field_name": self.field_name,
            "competing_values": self.competing_values,
            "resolved_value": self.resolved_value,
            "resolution_strategy": self.resolution_strategy,
            "explanation": self.explanation
        }


@dataclass
class CanonicalProfile:
    """Unified canonical candidate profile schema."""
    candidate_id: str = field(default_factory=lambda: f"CAN-{uuid.uuid4().hex[:8].upper()}")
    name: Optional[FieldValue] = None
    email: Optional[FieldValue] = None
    phone: Optional[FieldValue] = None
    skills: Optional[FieldValue] = None  # List of normalized skills
    experience_years: Optional[FieldValue] = None
    education: Optional[FieldValue] = None
    location: Optional[FieldValue] = None
    title: Optional[FieldValue] = None
    merged_source_ids: List[str] = field(default_factory=list)
    overall_confidence: float = 1.0
    conflicts: List[ConflictRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "candidate_id": self.candidate_id,
            "overall_confidence": round(self.overall_confidence, 4),
            "merged_sources": self.merged_source_ids,
            "profile": {}
        }
        
        for key in ["name", "email", "phone", "skills", "experience_years", "education", "location", "title"]:
            val = getattr(self, key)
            if val is not None:
                result["profile"][key] = val.to_dict()

        if self.conflicts:
            result["conflicts"] = [c.to_dict() for c in self.conflicts]
            
        return result


@dataclass
class DuplicateMatch:
    """Represents a potential or verified duplicate relationship between records."""
    record_id_1: str
    record_id_2: str
    similarity_score: float
    matching_attributes: Dict[str, float]
    status: str  # "DUPLICATE", "POSSIBLE_MATCH", "UNIQUE"
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id_1": self.record_id_1,
            "record_id_2": self.record_id_2,
            "similarity_score": round(self.similarity_score, 4),
            "matching_attributes": {k: round(v, 4) for k, v in self.matching_attributes.items()},
            "status": self.status,
            "explanation": self.explanation
        }


@dataclass
class PipelineResult:
    """Container for the output of the full ingestion and transformation pipeline."""
    canonical_profiles: List[CanonicalProfile]
    duplicate_matches: List[DuplicateMatch]
    total_raw_records: int
    processed_count: int
    failed_records: List[Dict[str, Any]]
    validation_report: Dict[str, Any]
    execution_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "total_raw_records": self.total_raw_records,
                "canonical_profiles_count": len(self.canonical_profiles),
                "duplicate_matches_found": len(self.duplicate_matches),
                "failed_records_count": len(self.failed_records),
                "execution_time_ms": round(self.execution_time_ms, 2)
            },
            "canonical_profiles": [p.to_dict() for p in self.canonical_profiles],
            "duplicates": [d.to_dict() for d in self.duplicate_matches],
            "failures": self.failed_records,
            "validation_report": self.validation_report
        }
