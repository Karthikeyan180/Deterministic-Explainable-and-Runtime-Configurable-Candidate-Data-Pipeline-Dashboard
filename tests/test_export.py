"""
Database & CSV Export Sink Unit Tests
"""

import unittest
import os
import sqlite3
import csv
import shutil
import tempfile
from src.pipeline import CandidateTransformationPipeline


class TestPipelineExportSinks(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="coe_export_test_")
        self.pipeline = CandidateTransformationPipeline()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sqlite_and_csv_export(self):
        res = self.pipeline.process_files(["data/sample_candidates.json", "data/sample_candidates.csv"])

        db_path = os.path.join(self.temp_dir, "test_candidates.db")
        csv_path = os.path.join(self.temp_dir, "test_candidates.csv")

        # Test SQLite Export
        self.pipeline.export_to_sqlite(res.canonical_profiles, db_path)
        self.assertTrue(os.path.exists(db_path))

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM canonical_candidates")
        count = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(count, len(res.canonical_profiles))

        # Test CSV Export
        self.pipeline.export_to_csv(res.canonical_profiles, csv_path)
        self.assertTrue(os.path.exists(csv_path))

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertEqual(len(rows), len(res.canonical_profiles))


if __name__ == "__main__":
    unittest.main()
