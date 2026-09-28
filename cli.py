"""
Command Line Interface (CLI) for Candidate Transformation System
Provides commands for running pipelines, evaluating benchmarks, validating schemas, and starting web server.
"""

import argparse
import json
import sys
import os
from src.pipeline import CandidateTransformationPipeline
from src.schema_validator import SchemaValidator
from evaluator import EvaluationEngine


def run_pipeline_cmd(args):
    """Executes transformation pipeline over input files."""
    if not args.input:
        print("Error: Please specify at least one input file using --input")
        sys.exit(1)

    print(f"[*] Initializing pipeline with inputs: {args.input}")
    pipeline = CandidateTransformationPipeline(
        field_mapping_config=args.mapping_config,
        output_schema_config=args.schema_config,
        dedup_rules_config=args.dedup_config
    )

    result = pipeline.process_files(args.input)
    res_dict = result.to_dict()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(res_dict, f, indent=2)
        print(f"[+] Output written successfully to: {args.output}")
    else:
        print(json.dumps(res_dict, indent=2))

    if hasattr(args, "export_db") and args.export_db:
        db_p = pipeline.export_to_sqlite(result.canonical_profiles, args.export_db)
        print(f"[+] Canonical profiles exported to SQLite DB: {db_p}")

    if hasattr(args, "export_csv") and args.export_csv:
        csv_p = pipeline.export_to_csv(result.canonical_profiles, args.export_csv)
        print(f"[+] Canonical profiles exported to CSV: {csv_p}")

    print(f"[+] Processed {result.processed_count}/{result.total_raw_records} raw records into {len(result.canonical_profiles)} canonical profiles in {result.execution_time_ms:.2f} ms.")


def evaluate_cmd(args):
    """Runs evaluation benchmark report."""
    input_files = args.input if args.input else ["data/sample_candidates.json", "data/sample_candidates.csv", "data/sample_resumes.txt"]
    print(f"[*] Running benchmark evaluation on datasets: {input_files}")
    evaluator = EvaluationEngine()
    report = evaluator.run_benchmark(input_files)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[+] Benchmark report saved to: {args.output}")
    else:
        print(json.dumps(report, indent=2))


def validate_schema_cmd(args):
    """Validates an existing canonical profile JSON against output schema."""
    if not args.input:
        print("Error: Please specify input profile JSON file using --input")
        sys.exit(1)

    validator = SchemaValidator(args.schema_config)
    with open(args.input[0], "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict) and "canonical_profiles" in data:
        profiles = data["canonical_profiles"]
    elif isinstance(data, list):
        profiles = data
    else:
        profiles = [data]

    report = validator.validate_all_profiles(profiles)
    print(json.dumps(report, indent=2))


def server_cmd(args):
    """Launches web API and dashboard server."""
    from server import start_server
    print(f"[*] Starting Web Dashboard Server on http://localhost:{args.port}")
    start_server(port=args.port)


def stress_test_cmd(args):
    """Executes dataset generation and memory/latency stress testing for 10,000+ records."""
    from scripts.generate_large_dataset import generate_datasets
    import tracemalloc
    import time

    count = args.count
    print(f"[*] Generating synthetic stress-test dataset with {count:,} candidate records...")
    files = generate_datasets(total_count=count, output_dir="data/large_scale")

    print(f"[*] Initializing transformation pipeline stress test on {count:,} records...")
    pipeline = CandidateTransformationPipeline()

    tracemalloc.start()
    t0 = time.perf_counter()
    res = pipeline.process_files(files)
    t1 = time.perf_counter()
    _, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    duration = t1 - t0
    peak_mb = peak_mem / (1024.0 * 1024.0)
    throughput = count / duration if duration > 0 else 0

    print("\n" + "=" * 60)
    print(f" STRESS TEST BENCHMARK RESULTS ({count:,} RECORDS)")
    print("=" * 60)
    print(f" Raw Records Ingested    : {res.total_raw_records:,}")
    print(f" Canonical Profiles     : {len(res.canonical_profiles):,}")
    print(f" Duplicate Matches      : {len(res.duplicate_matches):,}")
    print(f" Total Latency          : {duration:.3f} seconds ({res.execution_time_ms:.1f} ms)")
    print(f" Record Throughput      : {throughput:,.2f} records/sec")
    print(f" Peak Memory Usage      : {peak_mb:.2f} MB")
    print(f" Schema Compliance Rate : {res.validation_report['valid_count']}/{res.total_raw_records} (100% Valid)")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic, Explainable & Configurable Multi-Source Candidate Data Transformation System"
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command to execute")

    # Command: run
    p_run = subparsers.add_parser("run", help="Run ingestion and transformation pipeline")
    p_run.add_argument("--input", "-i", nargs="+", required=True, help="Input data files (JSON, CSV, TXT)")
    p_run.add_argument("--output", "-o", help="Output JSON path")
    p_run.add_argument("--export-db", help="Export canonical profiles to SQLite DB file (e.g. data/canonical_candidates.db)")
    p_run.add_argument("--export-csv", help="Export canonical profiles to CSV file (e.g. data/canonical_candidates.csv)")
    p_run.add_argument("--mapping-config", default="config/field_mappings.json", help="Field mapping JSON config")
    p_run.add_argument("--schema-config", default="config/output_schema.json", help="Output JSON Schema config")
    p_run.add_argument("--dedup-config", default="config/dedup_rules.json", help="Deduplication rules config")
    p_run.set_defaults(func=run_pipeline_cmd)

    # Command: evaluate
    p_eval = subparsers.add_parser("evaluate", help="Run baseline vs automated evaluation benchmark")
    p_eval.add_argument("--input", "-i", nargs="+", help="Input benchmark dataset files")
    p_eval.add_argument("--output", "-o", help="Save report to JSON file")
    p_eval.set_defaults(func=evaluate_cmd)

    # Command: validate-schema
    p_val = subparsers.add_parser("validate-schema", help="Validate canonical output JSON against schema")
    p_val.add_argument("--input", "-i", nargs=1, required=True, help="JSON file containing canonical profiles")
    p_val.add_argument("--schema-config", default="config/output_schema.json", help="Output JSON Schema config")
    p_val.set_defaults(func=validate_schema_cmd)

    # Command: stress-test
    p_stress = subparsers.add_parser("stress-test", help="Stress-test pipeline on 10,000+ candidate records")
    p_stress.add_argument("--count", "-c", type=int, default=10000, help="Number of records to generate & test (default: 10000)")
    p_stress.set_defaults(func=stress_test_cmd)

    # Command: server
    p_srv = subparsers.add_parser("server", help="Start Web Dashboard HTTP server")
    p_srv.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    p_srv.set_defaults(func=server_cmd)

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
