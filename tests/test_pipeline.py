"""
Comprehensive Unit & Integration Test Suite
Tests data ingestion, field mapping, normalization, deduplication, conflict resolution, provenance, confidence scoring, and end-to-end pipeline execution.
"""

import unittest
import os
import json
from src.ingestion import IngestionEngine
from src.field_mapper import FieldMapper
from src.normalization import DataNormalizer
from src.deduplication import DeduplicationEngine, jaro_winkler_similarity
from src.conflict_resolution import ConflictResolver
from src.provenance_scoring import ConfidenceScorer
from src.schema_validator import SchemaValidator
from src.pipeline import CandidateTransformationPipeline
from evaluator import EvaluationEngine


class TestCandidateTransformationSystem(unittest.TestCase):

    def setUp(self):
        self.mapping_config = "config/field_mappings.json"
        self.schema_config = "config/output_schema.json"
        self.dedup_config = "config/dedup_rules.json"

    def test_normalization_email(self):
        norm = DataNormalizer()
        val, rules = norm.normalize_email("  RAHUL@GMAIL.COM ")
        self.assertEqual(val, "rahul@gmail.com")
        self.assertIn("lowercased", rules)

        val_mailto, rules_m = norm.normalize_email("mailto:priya@techcorp.com")
        self.assertEqual(val_mailto, "priya@techcorp.com")
        self.assertIn("stripped_mailto_prefix", rules_m)

    def test_normalization_phone(self):
        norm = DataNormalizer()
        val, rules = norm.normalize_phone("+1 (555) 019-2834")
        self.assertEqual(val, "+15550192834")
        self.assertIn("removed_non_digits", rules)

    def test_normalization_experience(self):
        norm = DataNormalizer()
        val, rules = norm.normalize_experience("24 months")
        self.assertEqual(val, 2.0)

        val2, rules2 = norm.normalize_experience("4.5 years")
        self.assertEqual(val2, 4.5)

    def test_normalization_skills(self):
        norm = DataNormalizer()
        skills, rules = norm.normalize_skills(["JAVA", "python", "React.js", "sql"])
        self.assertIn("Java", skills)
        self.assertIn("Python", skills)
        self.assertIn("React", skills)
        self.assertIn("SQL", skills)

    def test_field_mapper(self):
        mapper = FieldMapper(self.mapping_config)
        raw_rec = {
            "candidate_name": "Rahul Kumar",
            "email_address": "rahul@gmail.com",
            "years_exp": "2 years"
        }
        mapped, key_map = mapper.map_raw_record(raw_rec)
        self.assertEqual(mapped.get("name"), "Rahul Kumar")
        self.assertEqual(mapped.get("email"), "rahul@gmail.com")
        self.assertEqual(mapped.get("experience_years"), "2 years")

    def test_jaro_winkler_similarity(self):
        score_exact = jaro_winkler_similarity("Rahul Kumar", "Rahul Kumar")
        self.assertEqual(score_exact, 1.0)

        score_similar = jaro_winkler_similarity("Rahul Kumar", "Rahul K")
        self.assertGreater(score_similar, 0.80)

        score_diff = jaro_winkler_similarity("Rahul Kumar", "Priya Sharma")
        self.assertLess(score_diff, 0.60)

    def test_deduplication_engine(self):
        engine = DeduplicationEngine(self.dedup_config)
        rec1 = {"record_id": "r1", "email": "rahul@gmail.com", "name": "Rahul Kumar"}
        rec2 = {"record_id": "r2", "email": "rahul@gmail.com", "name": "Rahul K"}

        match = engine.compare_records(rec1, rec2)
        self.assertEqual(match.status, "DUPLICATE")
        self.assertGreaterEqual(match.similarity_score, 0.85)

    def test_schema_validator(self):
        validator = SchemaValidator(self.schema_config)
        sample_profile = {
            "candidate_id": "CAN-12345678",
            "overall_confidence": 0.95,
            "merged_sources": ["resume.json"],
            "profile": {
                "name": {"value": "Rahul Kumar", "confidence": 0.95},
                "email": {"value": "rahul@gmail.com", "confidence": 0.99}
            }
        }
        is_valid, errors = validator.validate_profile(sample_profile)
        self.assertTrue(is_valid, f"Validation failed with errors: {errors}")

    def test_full_pipeline_execution(self):
        pipeline = CandidateTransformationPipeline(
            field_mapping_config=self.mapping_config,
            output_schema_config=self.schema_config,
            dedup_rules_config=self.dedup_config
        )

        input_files = ["data/sample_candidates.json", "data/sample_candidates.csv", "data/sample_resumes.txt"]
        result = pipeline.process_files(input_files)

        self.assertGreater(result.total_raw_records, 0)
        self.assertGreater(len(result.canonical_profiles), 0)
        self.assertTrue(result.validation_report["valid_count"] > 0)
        self.assertEqual(result.validation_report["invalid_count"], 0)

    def test_evaluation_engine(self):
        evaluator = EvaluationEngine()
        report = evaluator.run_benchmark(["data/sample_candidates.json", "data/sample_candidates.csv"])
        self.assertIn("baseline_vs_proposed", report)
        self.assertGreater(report["baseline_vs_proposed"]["task_time_seconds"]["improvement_pct"], 10.0)


if __name__ == "__main__":
    unittest.main()
