"""
Main Candidate Transformation Pipeline Orchestrator
Coordinates Ingestion -> Field Mapping -> Normalization -> Deduplication -> Conflict Resolution -> Provenance & Confidence Scoring -> Schema Validation.
"""

import time
from typing import List, Dict, Any, Optional
from src.models import (
    RawRecord, CanonicalProfile, FieldValue, ProvenanceEntry,
    ConflictRecord, PipelineResult
)
from src.ingestion import IngestionEngine
from src.field_mapper import FieldMapper
from src.normalization import DataNormalizer
from src.deduplication import DeduplicationEngine
from src.conflict_resolution import ConflictResolver
from src.provenance_scoring import ConfidenceScorer
from src.schema_validator import SchemaValidator


class CandidateTransformationPipeline:
    """End-to-end multi-source candidate transformation pipeline."""

    def __init__(
        self,
        field_mapping_config: str = "config/field_mappings.json",
        output_schema_config: str = "config/output_schema.json",
        dedup_rules_config: str = "config/dedup_rules.json"
    ):
        self.ingestion_engine = IngestionEngine()
        self.field_mapper = FieldMapper(field_mapping_config)
        self.normalizer = DataNormalizer()
        self.dedup_engine = DeduplicationEngine(dedup_rules_config)
        self.conflict_resolver = ConflictResolver(self.field_mapper)
        self.confidence_scorer = ConfidenceScorer(self.field_mapper)
        self.schema_validator = SchemaValidator(output_schema_config)

    def process_files(self, file_paths: List[str]) -> PipelineResult:
        """
        Executes pipeline over a list of input file paths (JSON, CSV, Text/Resume).
        """
        start_time = time.time()

        all_raw_records: List[RawRecord] = []
        all_failures: List[Dict[str, Any]] = []

        # Stage 1: Data Ingestion
        for fp in file_paths:
            recs, fails = self.ingestion_engine.ingest_file(fp)
            all_raw_records.extend(recs)
            all_failures.extend(fails)

        # Stage 2: Field Mapping & Data Normalization for each record
        normalized_records = []
        for raw_rec in all_raw_records:
            norm_rec = self._process_single_raw_record(raw_rec)
            normalized_records.append(norm_rec)

        # Stage 3: Deduplication & Cluster Matching
        clusters, duplicate_matches = self.dedup_engine.find_all_duplicates(
            [r["normalized_data"] for r in normalized_records]
        )

        # Stage 4 & 5: Multi-source Merge, Conflict Resolution, Provenance & Confidence Scoring
        canonical_profiles: List[CanonicalProfile] = []
        for cluster_indices in clusters:
            cluster_recs = [normalized_records[idx] for idx in cluster_indices]
            canonical = self._merge_cluster_into_canonical(cluster_recs)
            canonical_profiles.append(canonical)

        # Stage 6: Schema Validation
        profile_dicts = [p.to_dict() for p in canonical_profiles]
        val_report = self.schema_validator.validate_all_profiles(profile_dicts)

        execution_time = (time.time() - start_time) * 1000.0

        return PipelineResult(
            canonical_profiles=canonical_profiles,
            duplicate_matches=duplicate_matches,
            total_raw_records=len(all_raw_records),
            processed_count=len(normalized_records),
            failed_records=all_failures,
            validation_report=val_report,
            execution_time_ms=execution_time
        )

    def _process_single_raw_record(self, raw_rec: RawRecord) -> Dict[str, Any]:
        """Maps fields and normalizes individual attribute values for a raw record."""
        mapped_data, raw_key_map = self.field_mapper.map_raw_record(raw_rec.raw_data)
        normalized_data = {"record_id": raw_rec.record_id, "source_id": raw_rec.source_id}
        transformations_applied = {}
        field_confidences = {}

        for canonical_key, val in mapped_data.items():
            norm_val, rules = self._normalize_field(canonical_key, val)
            normalized_data[canonical_key] = norm_val
            transformations_applied[canonical_key] = rules

            conf = self.confidence_scorer.compute_field_confidence(
                field_name=canonical_key,
                value=norm_val,
                source_id=raw_rec.source_id,
                transformation_rules=rules
            )
            field_confidences[canonical_key] = conf

        return {
            "raw_record": raw_rec,
            "mapped_data": mapped_data,
            "raw_key_map": raw_key_map,
            "normalized_data": normalized_data,
            "transformations": transformations_applied,
            "confidences": field_confidences
        }

    def _normalize_field(self, field_name: str, val: Any) -> Tuple[Any, List[str]]:
        """Invokes appropriate normalization method for given field name."""
        if field_name == "email":
            return self.normalizer.normalize_email(val)
        elif field_name == "phone":
            return self.normalizer.normalize_phone(val)
        elif field_name == "name":
            return self.normalizer.normalize_name(val)
        elif field_name == "experience_years":
            return self.normalizer.normalize_experience(val)
        elif field_name == "skills":
            return self.normalizer.normalize_skills(val)
        elif field_name == "education":
            return self.normalizer.normalize_education(val)
        elif field_name == "location":
            return self.normalizer.normalize_location(val)
        elif field_name == "title":
            return self.normalizer.normalize_title(val)
        else:
            return val, ["unmodified"]

    def _merge_cluster_into_canonical(self, cluster_recs: List[Dict[str, Any]]) -> CanonicalProfile:
        """Merges a cluster of matched records into a single CanonicalProfile."""
        profile = CanonicalProfile()
        merged_sources = set()

        for rec in cluster_recs:
            merged_sources.add(rec["raw_record"].source_id)
        profile.merged_source_ids = list(merged_sources)

        all_canonical_fields = ["name", "email", "phone", "skills", "experience_years", "education", "location", "title"]

        for f_name in all_canonical_fields:
            competing = []
            for rec in cluster_recs:
                norm_data = rec["normalized_data"]
                if f_name in norm_data and norm_data[f_name] is not None:
                    raw_k = rec["raw_key_map"].get(f_name, f_name)
                    raw_v = rec["raw_record"].raw_data.get(raw_k, norm_data[f_name])
                    competing.append({
                        "value": norm_data[f_name],
                        "source_id": rec["raw_record"].source_id,
                        "confidence": rec["confidences"].get(f_name, 0.8),
                        "raw_key": raw_k,
                        "raw_value": raw_v,
                        "transformation_rules": rec["transformations"].get(f_name, []),
                        "timestamp": rec["raw_record"].timestamp
                    })

            if competing:
                fv, conf_record = self.conflict_resolver.resolve_field_conflict(
                    field_name=f_name,
                    competing_values=competing,
                    strategy="highest_confidence"
                )
                setattr(profile, f_name, fv)
                if conf_record:
                    profile.conflicts.append(conf_record)

        # Compute aggregate profile confidence
        profile.overall_confidence = self.confidence_scorer.compute_overall_profile_confidence(profile)
        return profile

    def export_to_sqlite(self, canonical_profiles: List[CanonicalProfile], db_path: str = "data/canonical_candidates.db") -> str:
        """Exports canonical profiles to a local SQLite database sink."""
        import sqlite3
        import os

        if os.path.dirname(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS canonical_candidates (
                candidate_id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                phone TEXT,
                title TEXT,
                location TEXT,
                experience_years REAL,
                skills TEXT,
                overall_confidence REAL,
                merged_sources TEXT,
                created_at REAL
            )
        """)

        for p in canonical_profiles:
            prof_dict = p.to_dict().get("profile", {})
            cand_id = p.candidate_id
            name = prof_dict.get("name", {}).get("value") if prof_dict.get("name") else None
            email = prof_dict.get("email", {}).get("value") if prof_dict.get("email") else None
            phone = prof_dict.get("phone", {}).get("value") if prof_dict.get("phone") else None
            title = prof_dict.get("title", {}).get("value") if prof_dict.get("title") else None
            loc = prof_dict.get("location", {}).get("value") if prof_dict.get("location") else None
            exp = prof_dict.get("experience_years", {}).get("value") if prof_dict.get("experience_years") else None
            skills_list = prof_dict.get("skills", {}).get("value", []) if prof_dict.get("skills") else []
            skills_str = ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list)
            conf = p.overall_confidence
            sources = ", ".join(p.merged_source_ids)

            cursor.execute("""
                INSERT OR REPLACE INTO canonical_candidates (
                    candidate_id, name, email, phone, title, location, experience_years, skills, overall_confidence, merged_sources, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cand_id, name, email, phone, title, loc, exp, skills_str, conf, sources, time.time()))

        conn.commit()
        conn.close()
        return db_path

    def export_to_csv(self, canonical_profiles: List[CanonicalProfile], csv_path: str = "data/canonical_candidates.csv") -> str:
        """Exports canonical profiles to a CSV spreadsheet sink."""
        import csv
        import os

        if os.path.dirname(csv_path):
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        headers = ["candidate_id", "name", "email", "phone", "title", "location", "experience_years", "skills", "overall_confidence", "merged_sources"]

        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for p in canonical_profiles:
                prof_dict = p.to_dict().get("profile", {})
                skills_list = prof_dict.get("skills", {}).get("value", []) if prof_dict.get("skills") else []
                writer.writerow({
                    "candidate_id": p.candidate_id,
                    "name": prof_dict.get("name", {}).get("value") if prof_dict.get("name") else "",
                    "email": prof_dict.get("email", {}).get("value") if prof_dict.get("email") else "",
                    "phone": prof_dict.get("phone", {}).get("value") if prof_dict.get("phone") else "",
                    "title": prof_dict.get("title", {}).get("value") if prof_dict.get("title") else "",
                    "location": prof_dict.get("location", {}).get("value") if prof_dict.get("location") else "",
                    "experience_years": prof_dict.get("experience_years", {}).get("value") if prof_dict.get("experience_years") else "",
                    "skills": ", ".join(skills_list) if isinstance(skills_list, list) else str(skills_list),
                    "overall_confidence": p.overall_confidence,
                    "merged_sources": ", ".join(p.merged_source_ids)
                })

        return csv_path
