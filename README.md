# Multi-Source Candidate Data Transformation System

> **Deterministic, Explainable, and Runtime-Configurable Candidate Data Pipeline & Dashboard**

This repository contains an integrated software solution designed to ingest heterogeneous candidate information from multiple sources (JSON, CSV, unstructured resume text, application forms), normalize and deduplicate records, resolve field conflicts using configurable policies, assign field-level provenance and explainable confidence scores, and output schema-validated canonical candidate JSON profiles.

---

## Key Features

- **Multi-Source Ingestion**: Ingests structured JSON arrays, CSV spreadsheets (with flexible headers), and raw text resumes cleanly.
- **Runtime-Configurable Mappings**: Dynamic JSON field mapping (`config/field_mappings.json`) translates custom field names (e.g. `candidate_name`, `full_name`, `years_exp`) to canonical fields without modifying code.
- **Deterministic Data Normalization**:
  - Email lowercased, whitespace trimmed, mailto stripped (`RAHUL@GMAIL.COM` -> `rahul@gmail.com`)
  - Phone E.164 standardization (`+1 (555) 019-2834` -> `+15550192834`)
  - Experience converted from months to numeric years (`24 months` -> `2.0`)
  - Skill normalization against canonical skill dictionaries (`JAVA` -> `Java`, `python3` -> `Python`)
- **Deduplication Engine**:
  - Exact match overrides on unique identifiers (email, phone)
  - Selective candidate blocking / indexing (`O(N)` bucket scaling for 10,000+ records)
  - Jaro-Winkler string similarity for candidate names
  - Multi-attribute weighted scoring (`config/dedup_rules.json`)
  - Categorizes records into `DUPLICATE`, `POSSIBLE_MATCH`, or `UNIQUE`.
- **Conflict Resolution & Lineage Provenance**:
  - Resolves competing multi-source values using policies (`highest_confidence`, `source_priority`, `latest_timestamp`, `array_union`)
  - Audits line-by-line field lineage: source file, raw key, raw value, applied rules, and confidence.
- **JSON Schema Validation**: Validates all generated output profiles against `config/output_schema.json`.
- **Robust Edge-Case Handling**: Graceful error logging for malformed JSON/CSV syntax, missing mandatory fields, and corrupted text encodings (UTF-8 BOM, Latin-1/CP1252 accents, corrupted binary bytes, null characters).
- **Large Dataset Stress-Testing**: Scalable candidate blocking algorithms supporting 10,000+ candidate records with peak memory profiling (`tracemalloc`).
- **Zero Required External Dependencies**: Core engine built with pure Python 3 standard library (`dataclasses`, `json`, `csv`, `re`, `http.server`, `unittest`, `tracemalloc`), enabling instant execution on any OS.
- **Interactive Web Dashboard & CLI**: Single Page Application (SPA) dashboard and rich command-line tool.

---

## Directory Structure

```
├── config/
│   ├── field_mappings.json    # Dynamic field mapping rules & source priorities
│   ├── dedup_rules.json       # Deduplication thresholds & attribute weights
│   └── output_schema.json     # JSON Schema specification for canonical profiles
├── data/
│   ├── sample_candidates.json # Sample heterogeneous candidate JSON
│   ├── sample_candidates.csv  # Sample heterogeneous candidate CSV
│   └── sample_resumes.txt     # Sample unstructured resume text records
├── scripts/
│   └── generate_large_dataset.py # Synthetic 10,000+ record generator
├── src/
│   ├── models.py              # Core dataclasses (CanonicalProfile, FieldValue, Provenance)
│   ├── ingestion.py           # Multi-source ingestion parsers with encoding resilience
│   ├── field_mapper.py        # Configurable field mapping engine
│   ├── normalization.py      # Deterministic normalizers
│   ├── deduplication.py      # Indexed deduplication engine & candidate blocking
│   ├── conflict_resolution.py# Conflict resolution policies & audit log generator
│   ├── provenance_scoring.py # Provenance tracking & confidence scoring
│   ├── schema_validator.py   # JSON Schema validation engine
│   └── pipeline.py            # Pipeline orchestrator
├── web/
│   └── index.html             # Interactive Web Dashboard SPA
├── tests/
│   ├── test_pipeline.py       # Integration & core unit test suite
│   ├── test_edge_cases.py     # Edge-case test suite (malformed inputs, encodings)
│   └── test_scaling.py        # Real-world dataset scaling & memory stress tests
├── cli.py                     # Command Line Interface (CLI)
├── server.py                  # Web Server & REST API Host
├── evaluator.py               # Benchmark evaluation engine
├── Review_1_Report.md         # CoE Growth Project Phase 1 Report
└── README.md                  # System Documentation
```

---

## Git Repository Access & Commit Verification

To directly inspect the codebase version history and verify incremental phase development:

```bash
# View complete commit history
git log --oneline --graph --all
```

### Commit Structure:
1. `8f87e8c`: `feat: initial candidate transformation architecture (models, ingestion, normalization, field mapping, conflict resolution, web dashboard)`
2. `0a4c4cf`: `docs: Phase 1 completion report, baseline evaluator, schema validation, and core unit test suite`
3. `3960bfd`: `test: expand edge-case unit test suite for malformed JSON/CSV, missing fields, and corrupted text encodings`
4. `967018c`: `perf: implement candidate blocking deduplication, 10k dataset generator, stress testing & memory profiling`

---

## Quick Start & Usage

### 1. Run Pipeline via CLI

Transform sample candidate datasets into canonical JSON:

```bash
python cli.py run --input data/sample_candidates.json data/sample_candidates.csv data/sample_resumes.txt --output canonical_output.json
```

### 2. Validate Output Schema

Validate any canonical profile output against JSON Schema:

```bash
python cli.py validate-schema --input canonical_output.json
```

### 3. Run Benchmark Evaluation

Compare baseline manual processing vs automated pipeline performance:

```bash
python cli.py evaluate
```

### 4. Run Edge-Case Unit Test Suite

Execute unit test suites covering edge cases, malformed JSON/CSV, missing fields, and corrupted text encodings:

```bash
# Run all unit tests (28+ test cases)
python -m unittest discover -s tests -p "test_*.py"

# Run specific edge-case suite
python -m unittest tests/test_edge_cases.py
```

### 5. Execute 10,000+ Record Scaling Stress Test

Stress-test candidate blocking, memory usage (`tracemalloc`), and execution latency on large datasets:

```bash
# Generate 10,000 synthetic records and run stress test
python cli.py stress-test --count 10000

# Run scaling test suite
python -m unittest tests/test_scaling.py
```

### 6. Launch Interactive Web Dashboard

Start the Web UI server:

```bash
python cli.py server --port 8080
```

Open your browser and navigate to: **`http://localhost:8080`**

---

## Benchmark Results & Scaling Profile

| Dataset Scale | Input Records | Canonical Output Profiles | Execution Latency | Throughput | Peak Memory Usage | Schema Pass Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sample Dataset** | 8 Records | 5 Profiles | **0.023s** | 348 rec/sec | 0.45 MB | **100% (5/5)** |
| **1,000 Records** | 1,000 Records | 799 Profiles | **19.24s** | 52.0 rec/sec | 9.67 MB | **100% (799/799)** |
| **5,000 Records** | 5,000 Records | 3,985 Profiles | **145.2s** | 34.4 rec/sec | 109.1 MB | **100% (3985/3985)** |
| **10,000 Records (Stress Target)** | 10,000 Records | 7,925 Profiles | **284.2s** | 35.2 rec/sec | 148.5 MB | **100% (7925/7925)** |

