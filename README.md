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
- **Human Override & Governance**:
  - Recruiter manual override modal on Web SPA & REST API (`/api/override`)
  - Automatically flags fields with low confidence (< 0.70) or active conflicts with visual warning badges
  - Persistent, immutable audit trail logging (`data/audit_log.json`) accessible via `/api/audit-trail`.
- **Database Export Sinks & Persistence**:
  - Relational SQLite database exporter (`export_to_sqlite()`) creating indexed relational tables (`canonical_candidates`, `candidate_skills`, `field_provenance`)
  - Flat CSV exporter (`export_to_csv()`) for BI tool ingestion.
- **AI Skill Match Scoring**: Intelligent candidate match scoring engine (`src/recommendation_engine.py`) ranking candidates against vacancy criteria (0-100%).
- **System Resilience & Concurrency**: Multi-threaded request isolation, corrupted payload recovery, and service interruption resilience.
- **JSON Schema Validation**: Validates all generated output profiles against `config/output_schema.json`.
- **Robust Edge-Case Handling**: Graceful error logging for malformed JSON/CSV syntax, missing mandatory fields, and corrupted text encodings (UTF-8 BOM, Latin-1/CP1252 accents, corrupted binary bytes, null characters).
- **Large Dataset Stress-Testing**: Scalable candidate blocking algorithms supporting 10,000+ candidate records with peak memory profiling (`tracemalloc`).
- **Zero Required External Dependencies**: Core engine built with pure Python 3 standard library (`dataclasses`, `sqlite3`, `json`, `csv`, `re`, `http.server`, `unittest`, `tracemalloc`, `threading`), enabling instant execution on any OS.
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
│   ├── sample_resumes.txt     # Sample unstructured resume text records
│   └── audit_log.json         # Persistent human override audit trail log
├── scripts/
│   └── generate_large_dataset.py # Synthetic 10,000+ record generator
├── src/
│   ├── models.py              # Dataclasses (CanonicalProfile, FieldValue, HumanOverride)
│   ├── ingestion.py           # Multi-source ingestion parsers with encoding resilience
│   ├── field_mapper.py        # Configurable field mapping engine
│   ├── normalization.py      # Deterministic normalizers
│   ├── deduplication.py      # Indexed deduplication engine & candidate blocking
│   ├── conflict_resolution.py# Conflict resolution policies & human override engine
│   ├── provenance_scoring.py # Provenance tracking & confidence scoring
│   ├── schema_validator.py   # JSON Schema validation engine
│   ├── recommendation_engine.py # Skill match scoring & suitability ranking engine
│   └── pipeline.py            # Pipeline orchestrator & DB/CSV export sinks
├── web/
│   └── index.html             # Interactive Web Dashboard SPA with Override Modal
├── tests/
│   ├── test_pipeline.py       # Integration & core unit test suite (10 tests)
│   ├── test_edge_cases.py     # Edge-case test suite (15 tests)
│   ├── test_scaling.py        # Real-world dataset scaling & memory stress tests (3 tests)
│   ├── test_resilience.py     # System resilience & concurrent request test suite (3 tests)
│   ├── test_recommendation.py # AI candidate skill match scoring tests (2 tests)
│   └── test_export.py         # SQLite & CSV database export sink tests (2 tests)
├── cli.py                     # Command Line Interface (CLI)
├── server.py                  # Web Server & REST API Host (/api/ingest, /api/override, /api/audit-trail)
├── evaluator.py               # Benchmark evaluation engine
├── Review_1_Report.md         # CoE Growth Project Phase 1 Report
├── Review_2_Report.md         # CoE Growth Project Phase 2 Report (70% Completion Submission)
└── README.md                  # System Documentation
```

---

## Quick Start & Usage

### 1. Run Pipeline via CLI (with SQLite & CSV Exports)

Transform sample candidate datasets into canonical JSON, SQLite database, and CSV profile sinks:

```bash
python cli.py run --input data/sample_candidates.json data/sample_candidates.csv data/sample_resumes.txt --output canonical_output.json --export-db output_candidates.db --export-csv output_candidates.csv
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

### 4. Run Comprehensive Automated Test Suites

Execute all 35 unit, edge-case, scaling, resilience, recommendation, and database export test cases:

```bash
# Run all unit tests (35 test cases)
python -m unittest discover -s tests -p "test_*.py"

# Run resilience test suite (concurrent API & service interruption)
python -m unittest tests/test_resilience.py

# Run edge-case test suite
python -m unittest tests/test_edge_cases.py

# Run database export test suite
python -m unittest tests/test_export.py

# Run recommendation engine test suite
python -m unittest tests/test_recommendation.py
```

### 5. Execute 10,000+ Record Scaling Stress Test

Stress-test candidate blocking, memory usage (`tracemalloc`), and execution latency on large datasets:

```bash
# Generate 10,000 synthetic records and run stress test
python cli.py stress-test --count 10000

# Run scaling test suite
python -m unittest tests/test_scaling.py
```

### 6. Launch Interactive Web Dashboard & Decision Support UI

Start the Web UI server:

```bash
python cli.py server --port 8080
```

Open your browser and navigate to: **`http://localhost:8080`**

---

## REST API Reference

The server ([server.py](file:///c:/Users/bloom/Desktop/COE%20project/server.py)) exposes REST endpoints built strictly on pure Python 3 `http.server`:

### 1. `POST /api/ingest`
Ingests raw candidate JSON payloads, normalizes and deduplicates them into canonical profiles, and returns validated output.

- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  [
    {
      "id": "CAND-001",
      "full_name": "Rahul Kumar",
      "email": "rahul@gmail.com",
      "phone": "+91 9876543210",
      "experience": "5 years",
      "skills": ["Java", "Python"]
    }
  ]
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "records_ingested": 1,
    "canonical_profiles": [
      {
        "id": "CAND-001",
        "name": "Rahul Kumar",
        "email": "rahul@gmail.com",
        "phone": "+919876543210",
        "experience_years": 5.0,
        "overall_confidence": 0.95,
        "has_conflicts": false,
        "provenance": { ... }
      }
    ]
  }
  ```
- **Error Response (400 Bad Request)**:
  ```json
  {
    "status": "error",
    "error": "Invalid JSON syntax: Expecting value: line 1 column 1 (char 0)"
  }
  ```

### 2. `POST /api/override`
Applies a recruiter human override to a specific candidate field, setting confidence to 1.0, updating provenance as `source_id: "human_override"`, clearing active conflict flags, and persisting the event to `data/audit_log.json`.

- **Content-Type**: `application/json`
- **Request Body**:
  ```json
  {
    "candidate_id": "CAND-001",
    "field_name": "experience_years",
    "old_value": 3.0,
    "new_value": 5.0,
    "reviewer_id": "recruiter_alex",
    "reason": "Verified candidate LinkedIn profile and confirmed 5 years of experience."
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Human override applied successfully",
    "candidate_id": "CAND-001",
    "field_name": "experience_years",
    "new_value": 5.0,
    "confidence": 1.0,
    "timestamp": "2026-09-28T18:30:00Z"
  }
  ```

### 3. `GET /api/audit-trail`
Retrieves the complete chronological audit log history of all automated pipeline decisions and manual human overrides.

- **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "audit_logs": [
      {
        "candidate_id": "CAND-001",
        "field_name": "experience_years",
        "old_value": 3.0,
        "new_value": 5.0,
        "reviewer_id": "recruiter_alex",
        "reason": "Verified candidate LinkedIn profile",
        "timestamp": "2026-09-28T18:30:00Z"
      }
    ]
  }
  ```

### 4. `GET /api/benchmark`
Triggers real-time synthetic dataset benchmarking and returns memory and latency metrics.

### 5. `GET /api/schema`
Returns the active JSON Schema definition (`config/output_schema.json`).

### 6. `GET /api/config`
Returns the active field mapping and deduplication configuration rules.

---

## Database Schema Documentation

When running with `--export-db output.db` or calling `export_to_sqlite()`, the pipeline creates an indexed, normalized relational SQLite database schema:

```
  ┌───────────────────────────┐         ┌───────────────────────────┐
  │   canonical_candidates    │ 1     * │     candidate_skills      │
  ├───────────────────────────┼─────────┼───────────────────────────┤
  │ id (PK, TEXT)             │         │ id (PK, AUTOINCREMENT)    │
  │ name (TEXT)               │         │ candidate_id (FK, TEXT)   │
  │ email (TEXT)              │         │ skill_name (TEXT)         │
  │ phone (TEXT)              │         └───────────────────────────┘
  │ experience_years (REAL)   │         ┌───────────────────────────┐
  │ location (TEXT)           │ 1     * │      field_provenance     │
  │ overall_confidence (REAL) │─────────┼───────────────────────────┤
  │ has_conflicts (INTEGER)   │         │ id (PK, AUTOINCREMENT)    │
  │ created_at (TEXT)         │         │ candidate_id (FK, TEXT)   │
  └───────────────────────────┘         │ field_name (TEXT)         │
                                        │ raw_value (TEXT)          │
                                        │ norm_value (TEXT)         │
                                        │ source_id (TEXT)          │
                                        │ confidence (REAL)         │
                                        └───────────────────────────┘
```

### Table 1: `canonical_candidates`
Stores normalized candidate profiles.

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `TEXT` | `PRIMARY KEY` | Unique candidate canonical ID (e.g. `CAND-001` or `REC-UUID`) |
| `name` | `TEXT` | `NOT NULL` | Normalized full candidate name |
| `email` | `TEXT` | Indexed | Lowercased, stripped E-mail address |
| `phone` | `TEXT` | Indexed | Standardized E.164 phone number |
| `experience_years` | `REAL` | — | Total work experience in floating-point years |
| `location` | `TEXT` | — | Title-cased candidate city/country location |
| `overall_confidence` | `REAL` | `NOT NULL` | Weighted profile confidence score (0.00 to 1.00) |
| `has_conflicts` | `INTEGER` | `NOT NULL` | Boolean flag (1 if unresolved field conflicts exist, else 0) |
| `created_at` | `TEXT` | `NOT NULL` | ISO 8601 UTC timestamp of canonical record creation |

- **Indexes**: `idx_cand_email` on `email`, `idx_cand_phone` on `phone`.

### Table 2: `candidate_skills`
Stores normalized candidate technical skills (1-to-many relationship).

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate primary key |
| `candidate_id` | `TEXT` | `FOREIGN KEY` | Reference to `canonical_candidates(id)` |
| `skill_name` | `TEXT` | `NOT NULL` | Standardized canonical skill (e.g., `Python`, `Java`) |

- **Index**: `idx_skill_cand` on `candidate_id`.

### Table 3: `field_provenance`
Stores field-level lineage, original values, and confidence scores (1-to-many relationship).

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY AUTOINCREMENT` | Surrogate primary key |
| `candidate_id` | `TEXT` | `FOREIGN KEY` | Reference to `canonical_candidates(id)` |
| `field_name` | `TEXT` | `NOT NULL` | Canonical field name (e.g., `email`, `experience_years`) |
| `raw_value` | `TEXT` | — | Raw value before normalization |
| `norm_value` | `TEXT` | — | Standardized canonical value |
| `source_id` | `TEXT` | `NOT NULL` | Provenance source identifier (file name or `"human_override"`) |
| `confidence` | `REAL` | `NOT NULL` | Field confidence score (0.00 to 1.00) |

- **Index**: `idx_prov_cand` on `candidate_id`.

---

## Technical Documentation on Unit Testing & Error Boundaries

### 1. Test Suite Architecture (35 Tests Across 6 Modules)

The system enforces rigorous automated testing built on Python 3 `unittest`:

```
                           [ Central Test Suite (35 Tests) ]
                                          │
       ┌──────────────────┬───────────────┼───────────────┬──────────────────┐
       ▼                  ▼               ▼               ▼                  ▼
[test_pipeline.py] [test_edge_cases.py] [test_scaling.py] [test_resilience.py] [test_export.py / test_recommendation.py]
  (10 Tests)         (15 Tests)         (3 Tests)       (3 Tests)          (4 Tests total)
```

1. **`tests/test_pipeline.py` (10 Tests)**:
   - Verifies end-to-end multi-source ingestion, field mapping, email/phone/experience normalization, Jaro-Winkler string similarity, deduplication merging, conflict resolution policies, and JSON Schema output validation.
2. **`tests/test_edge_cases.py` (15 Tests)**:
   - Focuses strictly on malformed inputs, boundary conditions, and corrupted data streams:
     - `test_malformed_json_syntax`: Verifies graceful failure logging on invalid JSON syntax without process crash.
     - `test_utf8_bom_decoding`: Tests transparent stripping of UTF-8 Byte Order Mark (`\xef\xbb\xbf`).
     - `test_latin1_cp1252_encoding`: Verifies decoding of non-UTF8 accent characters (`Renée`, `Müller`).
     - `test_binary_and_null_bytes`: Verifies stripping of corrupted binary streams and null bytes (`\x00`).
     - `test_missing_candidate_id_fallback`: Tests automatic `REC-` UUID fallback generation when candidate IDs are missing.
     - `test_column_mismatched_csv`: Verifies handling of CSV rows with extra or missing column headers.
     - `test_primitive_json_root`: Verifies soft failure error reporting when JSON root is an integer or string instead of dict/list.
3. **`tests/test_scaling.py` (3 Tests)**:
   - Profiling deduplication candidate blocking algorithms on 1,000 to 10,000+ candidate records.
   - Monitors peak memory usage via `tracemalloc` (capping peak allocation at ~95-148 MB for 10,000 records).
4. **`tests/test_resilience.py` (3 Tests)**:
   - Evaluates multi-threaded REST API execution (`ThreadPoolExecutor`), verifying thread safety during simultaneous ingestion and override requests.
   - Tests server recovery from truncated payloads, invalid Content-Length headers, and malformed POST parameters.
5. **`tests/test_recommendation.py` (2 Tests)**:
   - Verifies AI candidate skill match scoring (0-100%) and suitability classification against job vacancy requirements.
6. **`tests/test_export.py` (2 Tests)**:
   - Verifies relational SQLite database table creation (`export_to_sqlite()`) and flat CSV sink generation (`export_to_csv()`).

### 2. Error Boundaries & Fallback Hierarchy

The system defines 5 strict error boundaries preventing unhandled runtime exceptions:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ERROR BOUNDARY 1: Ingestion File & Character Encoding Boundary                         │
│ - Catch: UnicodeDecodeError, FileNotFoundError, PermissionError                         │
│ - Fallback: Try UTF-8 -> UTF-8 BOM -> Latin-1/CP1252 -> UTF-8 replace. Strip \x00 bytes.│
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ERROR BOUNDARY 2: Input Syntax & Structural Boundary                                   │
│ - Catch: json.JSONDecodeError, csv.Error, AttributeError, TypeError                     │
│ - Fallback: Record isolated failure dict in failures list; continue processing valid. │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ERROR BOUNDARY 3: Identifier & Attribute Normalization Boundary                        │
│ - Catch: Missing ID, empty string, invalid phone/email regex                           │
│ - Fallback: Assign REC-{TYPE}-{UUID} ID; retain raw value with confidence = 0.50.      │
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ERROR BOUNDARY 4: REST API Server & Concurrency Boundary                               │
│ - Catch: Malformed HTTP body, missing POST fields, client socket drops                  │
│ - Fallback: Return structured JSON {"status":"error", "error":"..."} with HTTP 400/500.│
└────────────────────────────────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ ERROR BOUNDARY 5: Database & Persistence Export Boundary                               │
│ - Catch: sqlite3.OperationalError, sqlite3.DatabaseError                             │
│ - Fallback: Rollback active transaction; log structured export error without crash.    │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Benchmark Results & Scaling Profile

| Dataset Scale | Input Records | Canonical Output Profiles | Duplicate Pairs Merged | Execution Latency | Throughput | Peak Memory Usage | Schema Pass Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Sample Dataset** | 8 Records | 5 Profiles | 2 Pairs | **0.023s** | 348 rec/sec | 0.45 MB | **100% (5/5)** |
| **1,000 Records** | 1,000 Records | 799 Profiles | 232 Pairs | **3.465s** | 288.59 rec/sec | 9.70 MB | **100% (799/799)** |
| **5,000 Records** | 5,000 Records | 3,985 Profiles | 1,147 Pairs | **23.151s** | 215.97 rec/sec | 47.94 MB | **100% (3985/3985)** |
| **10,000 Records (Stress Target)** | 10,000 Records | 7,925 Profiles | 2,336 Pairs | **100.287s** | 99.71 rec/sec | 95.89 MB | **100% (7925/7925)** |
