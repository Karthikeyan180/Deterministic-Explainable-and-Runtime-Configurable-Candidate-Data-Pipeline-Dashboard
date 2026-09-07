"""
Comprehensive Edge-Case Unit Test Suite
Explicitly tests malformed JSON/CSV inputs, missing mandatory fields, corrupted text encodings, and pipeline resilience.
"""

import unittest
import os
import json
import tempfile
import shutil
from src.ingestion import IngestionEngine
from src.field_mapper import FieldMapper
from src.normalization import DataNormalizer
from src.deduplication import DeduplicationEngine, jaro_winkler_similarity, jaccard_similarity
from src.conflict_resolution import ConflictResolver
from src.provenance_scoring import ConfidenceScorer
from src.schema_validator import SchemaValidator
from src.pipeline import CandidateTransformationPipeline


class TestEdgeCaseCoverage(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="coe_edge_cases_")
        self.mapping_config = "config/field_mappings.json"
        self.schema_config = "config/output_schema.json"
        self.dedup_config = "config/dedup_rules.json"
        self.ingestion = IngestionEngine()
        self.normalizer = DataNormalizer()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # ---------------------------------------------------------
    # 1. Malformed JSON Input Tests
    # ---------------------------------------------------------

    def test_malformed_json_syntax_error(self):
        file_path = os.path.join(self.test_dir, "syntax_error.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('{"candidate_name": "Rahul", "email": "rahul@gmail.com"')  # Unclosed brace

        valid, failures = self.ingestion.ingest_json_file(file_path, "syntax_error.json")
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(failures), 1)
        self.assertIn("Invalid JSON syntax", failures[0]["error"])

    def test_json_root_not_dict_or_list(self):
        file_path = os.path.join(self.test_dir, "primitive_root.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write('"Just a string root"')

        valid, failures = self.ingestion.ingest_json_file(file_path, "primitive_root.json")
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(failures), 1)
        self.assertIn("JSON root must be an object or an array", failures[0]["error"])

    def test_json_array_with_non_dict_items(self):
        file_path = os.path.join(self.test_dir, "invalid_array_items.json")
        data = [{"name": "Valid Candidate"}, "Invalid String Item", 12345, None]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        valid, failures = self.ingestion.ingest_json_file(file_path, "invalid_array_items.json")
        self.assertEqual(len(valid), 1)
        self.assertEqual(len(failures), 3)

    def test_empty_json_file(self):
        file_path = os.path.join(self.test_dir, "empty.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")

        valid, failures = self.ingestion.ingest_json_file(file_path, "empty.json")
        self.assertEqual(len(valid), 0)
        self.assertEqual(len(failures), 1)

    # ---------------------------------------------------------
    # 2. Malformed CSV Input Tests
    # ---------------------------------------------------------

    def test_malformed_csv_mismatched_columns(self):
        file_path = os.path.join(self.test_dir, "mismatched.csv")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("name,email,experience\n")
            f.write("Rahul Kumar,rahul@gmail.com,5 years,extra_value_1,extra_value_2\n")
            f.write("Priya Sharma\n")

        valid, failures = self.ingestion.ingest_csv_file(file_path, "mismatched.csv")
        self.assertGreaterEqual(len(valid), 1)

    def test_csv_delimiters_and_stray_quotes(self):
        file_path = os.path.join(self.test_dir, "tsv_format.tsv")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("candidate_name\temail_address\tyears_exp\n")
            f.write("Rahul\trahul@tech.com\t24 months\n")

        valid, failures = self.ingestion.ingest_csv_file(file_path, "tsv_format.tsv")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].raw_data.get("candidate_name"), "Rahul")

    def test_csv_all_blank_rows(self):
        file_path = os.path.join(self.test_dir, "blank_rows.csv")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("name,email\n\n  \n,,\n  ,  \n")

        valid, failures = self.ingestion.ingest_csv_file(file_path, "blank_rows.csv")
        self.assertEqual(len(valid), 0)

    # ---------------------------------------------------------
    # 3. Missing Mandatory Fields Tests
    # ---------------------------------------------------------

    def test_missing_candidate_id_auto_fallback(self):
        file_path = os.path.join(self.test_dir, "no_id.json")
        data = [{"name": "Rahul Kumar", "email": "rahul@gmail.com"}]
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        valid, failures = self.ingestion.ingest_json_file(file_path, "no_id.json")
        self.assertEqual(len(valid), 1)
        self.assertTrue(valid[0].record_id.startswith("REC-JSON-"))

    def test_missing_all_contact_fields(self):
        rec = {"record_id": "r_empty", "skills": ["Python"]}
        norm_email, _ = self.normalizer.normalize_email(rec.get("email"))
        norm_phone, _ = self.normalizer.normalize_phone(rec.get("phone"))
        self.assertIsNone(norm_email)
        self.assertIsNone(norm_phone)

        engine = DeduplicationEngine(self.dedup_config)
        match = engine.compare_records(rec, {"record_id": "r_empty_2", "skills": ["Java"]})
        self.assertEqual(match.status, "UNIQUE")

    def test_schema_validator_missing_required_fields(self):
        validator = SchemaValidator(self.schema_config)
        invalid_profile = {
            # Missing candidate_id, overall_confidence, merged_sources
            "profile": {
                "name": {"value": "Rahul"}
            }
        }
        is_valid, errors = validator.validate_profile(invalid_profile)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    # ---------------------------------------------------------
    # 4. Corrupted Text Encodings Tests
    # ---------------------------------------------------------

    def test_utf8_with_bom_encoding(self):
        file_path = os.path.join(self.test_dir, "bom_utf8.json")
        data = [{"name": "BOM Candidate", "email": "bom@example.com"}]
        with open(file_path, "w", encoding="utf-8-sig") as f:
            json.dump(data, f)

        valid, failures = self.ingestion.ingest_json_file(file_path, "bom_utf8.json")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].raw_data.get("name"), "BOM Candidate")

    def test_latin1_cp1252_encoding_accents(self):
        file_path = os.path.join(self.test_dir, "latin1_resume.txt")
        content = "Name: Renée Müller\nEmail: renee.muller@domain.de\nExperience: 5 years\n"
        with open(file_path, "wb") as f:
            f.write(content.encode("latin-1"))

        valid, failures = self.ingestion.ingest_text_file(file_path, "latin1_resume.txt")
        self.assertEqual(len(valid), 1)
        self.assertIn("Renée", valid[0].raw_data.get("name", ""))

    def test_corrupted_byte_sequences(self):
        file_path = os.path.join(self.test_dir, "corrupted_bytes.txt")
        corrupted_data = b"Name: Rahul Kumar\nEmail: rahul@gmail.com\x80\x81\xff\xfe\nExperience: 3 years"
        with open(file_path, "wb") as f:
            f.write(corrupted_data)

        valid, failures = self.ingestion.ingest_text_file(file_path, "corrupted_bytes.txt")
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0].raw_data.get("email"), "rahul@gmail.com")

    def test_embedded_null_bytes_in_text(self):
        file_path = os.path.join(self.test_dir, "null_bytes.txt")
        content = "Name: Priya\x00 Sharma\nEmail: priya@tech.com\x00\n"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        valid, failures = self.ingestion.ingest_text_file(file_path, "null_bytes.txt")
        self.assertEqual(len(valid), 1)

    # ---------------------------------------------------------
    # 5. Full Pipeline End-to-End Resilience
    # ---------------------------------------------------------

    def test_pipeline_mixed_valid_and_malformed_files(self):
        f_json = os.path.join(self.test_dir, "valid.json")
        with open(f_json, "w", encoding="utf-8") as f:
            json.dump([{"candidate_name": "Rahul", "email": "rahul@gmail.com"}], f)

        f_bad_json = os.path.join(self.test_dir, "bad.json")
        with open(f_bad_json, "w", encoding="utf-8") as f:
            f.write("{malformed json")

        pipeline = CandidateTransformationPipeline(
            field_mapping_config=self.mapping_config,
            output_schema_config=self.schema_config,
            dedup_rules_config=self.dedup_config
        )

        res = pipeline.process_files([f_json, f_bad_json])
        self.assertEqual(res.total_raw_records, 1)
        self.assertEqual(len(res.failed_records), 1)
        self.assertEqual(len(res.canonical_profiles), 1)


if __name__ == "__main__":
    unittest.main()
