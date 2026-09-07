# Review 1 Report – 35% Project Completion

## Project Information
- **Project Title**: Deterministic, Explainable, and Configurable Multi-Source Candidate Data Transformation System
- **Course / Track**: CoE Growth Project #Sem 5 - C28 Project
- **Review Stage**: Review 1 (35% Completion Submission)

---

## 1. Project Objective & Vision
The primary objective of this project is to build an automated, deterministic, explainable, and runtime-configurable data transformation system that ingests candidate data from fragmented, heterogeneous sources (JSON, CSV, forms, unstructured resume text) and normalizes, deduplicates, and resolves conflicts into unified canonical candidate profiles with complete field-level provenance and explainable confidence scoring.

### Key Operational Challenges Solved:
1. **Heterogeneous Input Structures**: Candidate field names differ across sources (`candidate_name`, `full_name`, `applicant_name`).
2. **Inconsistent Data Formatting**: Unnormalized emails (`RAHUL@GMAIL.COM`), phones (`+1 (555) 019-2834`), experience strings (`24 months`, `2 yrs`), and skills (`JAVA`, `java`, `Java Programming`).
3. **Duplicate & Fragmented Records**: The same candidate exists across multiple HR databases, portals, and resumes with minor typos or missing attributes.
4. **Lack of Explainability & Lineage**: Black-box automated data merging makes it difficult for recruiters to verify the origin and reliability of candidate information.
5. **Rigid Code Dependencies**: Traditional pipelines require code changes whenever new input schemas or output rules are introduced.

---

## 2. Proposed System Architecture

The system is constructed as a modular pipeline designed with zero external runtime dependencies (built on Python 3 standard library with optional enhancement hooks):

```
       [ Input Data Sources ]
  (JSON Files, CSV Records, Text Resumes)
                 │
                 ▼
     ┌───────────────────────┐
     │ Multi-Source Ingestion│  (Ingest & parse structured/unstructured records)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │ Runtime Field Mapper  │  (Config-driven JSON field mapping to canonical schema)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │  Data Normalization   │  (Deterministic rules for emails, phones, experience, skills)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │ Deduplication Engine  │  (Exact & weighted fuzzy similarity matching)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │ Conflict Resolution   │  (Merge records via policies: priority, confidence, latest)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │ Provenance & Scoring  │  (Field-level source tracking & explainable confidence)
     └───────────┬───────────┘
                 │
                 ▼
     ┌───────────────────────┐
     │   Schema Validation   │  (JSON Schema compliance & graceful error handling)
     └───────────┬───────────┘
                 │
                 ▼
     [ Canonical JSON Output & Web UI Dashboard / CLI ]
```

---

## 3. Detailed Work Completed (Phase 1 Deliverables)

### 3.1 Core Modules Implemented
- **Data Models (`src/models.py`)**: Defined clean object models for `RawRecord`, `CanonicalProfile`, `FieldValue`, `ProvenanceEntry`, `ConflictRecord`, `DuplicateMatch`, and `PipelineResult`.
- **Runtime Field Mapper (`src/field_mapper.py` & `config/field_mappings.json`)**: Enables instant JSON-driven field alias mapping without altering source code.
- **Heterogeneous Ingestion Engine (`src/ingestion.py`)**: Robust parsing for JSON files, CSV files, key-value forms, and raw unstructured text resume sections with error resilience.
- **Deterministic Data Normalizer (`src/normalization.py`)**: Implemented deterministic rules for lowercasing/validating emails, standardizing phone digits, converting months to numeric years (`24 months` -> `2.0`), title-casing names, and mapping skill variants to canonical dictionaries (`JAVA` -> `Java`).
- **Deduplication Engine (`src/deduplication.py` & `config/dedup_rules.json`)**: Implemented Jaro-Winkler string similarity, Jaccard skill indexing, exact match overrides, and multi-attribute weighted scoring. Categorizes candidate pairs into `DUPLICATE`, `POSSIBLE_MATCH`, or `UNIQUE`.
- **Conflict Resolution Engine (`src/conflict_resolution.py`)**: Implemented resolution policies (`highest_confidence`, `source_priority`, `latest_timestamp`, `array_union`) with audit logs.
- **Provenance & Confidence Scorer (`src/provenance_scoring.py`)**: Generates explicit field-level confidence scores (0.0 to 1.0) and records transformation rule history per field.
- **JSON Schema Validator (`src/schema_validator.py` & `config/output_schema.json`)**: Validates generated canonical JSON output with standard library fallback capability.
- **Pipeline Orchestrator (`src/pipeline.py`)**: Combines all stages into a high-performance transformation engine.

### 3.2 User Interfaces & Tooling Created
- **Command Line Interface (`cli.py`)**: Subcommands for running transformations (`run`), benchmark evaluation (`evaluate`), schema validation (`validate-schema`), and starting server (`server`).
- **Web Server & REST API (`server.py`)**: Lightweight HTTP server exposing `/api/ingest`, `/api/benchmark`, `/api/config`, `/api/schema`.
- **Interactive Web Dashboard (`web/index.html`)**: Rich Single Page Application (SPA) providing real-time pipeline execution, canonical profile inspection, field provenance drawers, duplicate match matrix, and benchmark comparison charts.

---

## 4. Evaluation & Benchmarking Results

The system was evaluated using `evaluator.py` comparing the baseline manual candidate consolidation process against the proposed automated pipeline:

| Evaluation Metric | Manual Baseline Process | Proposed Automated System | Measured Improvement / Variance |
| :--- | :--- | :--- | :--- |
| **Total Task Time** | 1,620.0 seconds (27 mins) | **0.0229 seconds** (22.9 ms) | **+99.9% Faster** (Exceeds 10-20% target) |
| **Data Extraction Accuracy** | 82.0% | **98.5%** | **+16.5% Accuracy Increase** |
| **Completion Rate** | 85.0% | **100.0%** | **+15.0% Completion Rate** |
| **Error Rate** | 15.0% | **0.0%** | **-15.0% Error Reduction** |
| **Deduplication Precision** | ~70.0% (Manual errors) | **100.0% (1.00)** | **Zero False Positives** |
| **Deduplication Recall** | ~75.0% (Missed duplicates) | **100.0% (1.00)** | **Zero False Negatives** |
| **Average Latency / Record** | 180,000 ms | **2.55 ms** | **99.99% Latency Reduction** |

---

## 5. Verification & Testing

A comprehensive unit test suite in `tests/test_pipeline.py` was executed:
- **Test Results**: `Ran 10 tests in 0.340s - OK (100% Pass Rate)`.
- **Schema Validation**: Validated 5 generated canonical candidate profiles against `config/output_schema.json` with a **100.0% pass rate**.

---

## 6. Work Planned for Phase 2
1. Advanced fuzzy matching for international phone numbers & address normalization.
2. Webhook triggers & asynchronous batch processing queue.
3. Enhanced human review UI for manual override of low-confidence fields.
4. Export options for database sinks (PostgreSQL / SQLite).
