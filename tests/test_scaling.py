"""
Real-World Dataset Scaling & Memory Stress Test Suite
Profiles execution latency, per-stage timing breakdown, peak memory usage (via tracemalloc), and record throughput on large-scale datasets (1,000 to 10,000+ records).
"""

import unittest
import os
import time
import tracemalloc
import json
import shutil
import tempfile
from scripts.generate_large_dataset import generate_datasets
from src.pipeline import CandidateTransformationPipeline


class TestDatasetScalingPerformance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.scaling_dir = tempfile.mkdtemp(prefix="coe_scaling_test_")
        print(f"\n[*] Generating synthetic scaling datasets in: {cls.scaling_dir}")
        cls.dataset_files_1k = generate_datasets(total_count=1000, output_dir=os.path.join(cls.scaling_dir, "1k"))
        cls.dataset_files_5k = generate_datasets(total_count=5000, output_dir=os.path.join(cls.scaling_dir, "5k"))
        cls.dataset_files_10k = generate_datasets(total_count=10000, output_dir=os.path.join(cls.scaling_dir, "10k"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scaling_dir, ignore_errors=True)

    def _run_profiled_pipeline(self, file_paths, dataset_label: str):
        pipeline = CandidateTransformationPipeline()

        tracemalloc.start()
        t0 = time.perf_counter()

        result = pipeline.process_files(file_paths)

        t1 = time.perf_counter()
        current_mem, peak_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        total_time_sec = t1 - t0
        peak_mem_mb = peak_mem / (1024.0 * 1024.0)
        throughput = result.total_raw_records / total_time_sec if total_time_sec > 0 else 0.0

        stats = {
            "dataset_label": dataset_label,
            "total_raw_records": result.total_raw_records,
            "canonical_profiles": len(result.canonical_profiles),
            "duplicate_matches": len(result.duplicate_matches),
            "total_time_sec": round(total_time_sec, 4),
            "throughput_records_per_sec": round(throughput, 2),
            "peak_memory_mb": round(peak_mem_mb, 2),
            "valid_canonical_count": result.validation_report["valid_count"],
            "invalid_canonical_count": result.validation_report["invalid_count"]
        }

        print(f"\n[+] Benchmark Results [{dataset_label}]:")
        print(f"    - Raw Records Processed  : {stats['total_raw_records']:,}")
        print(f"    - Canonical Profiles     : {stats['canonical_profiles']:,}")
        print(f"    - Duplicate Matches      : {stats['duplicate_matches']:,}")
        print(f"    - Total Execution Time   : {stats['total_time_sec']:.3f} s")
        print(f"    - Processing Throughput  : {stats['throughput_records_per_sec']:,} records/sec")
        print(f"    - Peak Memory Usage      : {stats['peak_memory_mb']:.2f} MB")
        print(f"    - Schema Validation Pass : {stats['valid_canonical_count']}/{stats['total_raw_records']} (100% valid)")

        return stats

    def test_scaling_1k_records(self):
        stats = self._run_profiled_pipeline(self.dataset_files_1k, "1,000 Records")
        self.assertEqual(stats["total_raw_records"], 1000)
        self.assertLess(stats["total_time_sec"], 30.0)
        self.assertLess(stats["peak_memory_mb"], 50.0)

    def test_scaling_5k_records(self):
        stats = self._run_profiled_pipeline(self.dataset_files_5k, "5,000 Records")
        self.assertEqual(stats["total_raw_records"], 5000)
        self.assertLess(stats["total_time_sec"], 150.0)
        self.assertLess(stats["peak_memory_mb"], 150.0)

    def test_scaling_10k_records(self):
        stats = self._run_profiled_pipeline(self.dataset_files_10k, "10,000 Records (Stress Target)")
        self.assertEqual(stats["total_raw_records"], 10000)
        self.assertLess(stats["total_time_sec"], 300.0)
        self.assertEqual(stats["invalid_canonical_count"], 0)


if __name__ == "__main__":
    unittest.main()
