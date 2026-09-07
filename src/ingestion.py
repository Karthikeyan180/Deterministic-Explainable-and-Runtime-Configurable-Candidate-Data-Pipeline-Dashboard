"""
Multi-Source Data Ingestion Module
Ingests heterogeneous candidate data from JSON, CSV, text/resume, and form formats.
"""

import csv
import json
import os
import re
import uuid
from typing import List, Dict, Any, Tuple
from src.models import RawRecord


class IngestionEngine:
    """Ingests candidate records from structured and unstructured sources gracefully."""

    def __init__(self):
        pass

    def ingest_file(self, file_path: str) -> Tuple[List[RawRecord], List[Dict[str, Any]]]:
        """
        Ingests a file based on its extension or content format.
        Returns (list_of_valid_raw_records, list_of_failed_or_malformed_records).
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = os.path.basename(file_path)
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".json":
            return self.ingest_json_file(file_path, filename)
        elif ext in [".csv", ".tsv"]:
            return self.ingest_csv_file(file_path, filename)
        elif ext in [".txt", ".md", ".log"]:
            return self.ingest_text_file(file_path, filename)
        else:
            # Fallback: try parsing as JSON first, then text
            try:
                return self.ingest_json_file(file_path, filename)
            except Exception:
                return self.ingest_text_file(file_path, filename)

    def _read_file_text(self, file_path: str) -> str:
        """Reads text content from file with fallback handling for UTF-8 BOM, Latin-1, CP1252, and corrupted byte sequences."""
        with open(file_path, "rb") as f:
            raw_bytes = f.read()

        # Handle UTF-8 BOM
        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            raw_bytes = raw_bytes[3:]

        try:
            content = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = raw_bytes.decode("latin-1")
            except Exception:
                content = raw_bytes.decode("utf-8", errors="replace")

        return content.replace("\x00", "")

    def ingest_json_file(self, file_path: str, source_id: str) -> Tuple[List[RawRecord], List[Dict[str, Any]]]:
        valid_records = []
        failures = []

        try:
            file_text = self._read_file_text(file_path).strip()
            if not file_text:
                failures.append({
                    "source_id": source_id,
                    "error": "Empty JSON file",
                    "file_path": file_path
                })
                return valid_records, failures

            content = json.loads(file_text)

            if isinstance(content, dict):
                content = [content]

            if not isinstance(content, list):
                failures.append({
                    "source_id": source_id,
                    "error": "JSON root must be an object or an array of objects",
                    "raw_content": str(content)[:200]
                })
                return valid_records, failures

            for idx, item in enumerate(content):
                if not isinstance(item, dict):
                    failures.append({
                        "source_id": source_id,
                        "index": idx,
                        "error": "JSON item is not a dictionary object",
                        "raw_item": str(item)[:200]
                    })
                    continue

                rec_id = item.get("id") or item.get("candidate_id") or f"REC-JSON-{uuid.uuid4().hex[:6]}"
                valid_records.append(RawRecord(
                    record_id=str(rec_id),
                    source_id=source_id,
                    source_type="json",
                    raw_data=item
                ))

        except json.JSONDecodeError as e:
            failures.append({
                "source_id": source_id,
                "error": f"Invalid JSON syntax: {str(e)}",
                "file_path": file_path
            })
        except Exception as e:
            failures.append({
                "source_id": source_id,
                "error": f"Error reading JSON file: {str(e)}",
                "file_path": file_path
            })

        return valid_records, failures

    def ingest_csv_file(self, file_path: str, source_id: str) -> Tuple[List[RawRecord], List[Dict[str, Any]]]:
        valid_records = []
        failures = []

        try:
            content = self._read_file_text(file_path)
            lines = [line for line in content.splitlines() if line.strip()]
            if not lines:
                return valid_records, failures

            sample = "\n".join(lines[:10])
            delimiter = ","
            if "\t" in sample and sample.count("\t") > sample.count(","):
                delimiter = "\t"
            elif ";" in sample and sample.count(";") > sample.count(","):
                delimiter = ";"

            reader = csv.DictReader(lines, delimiter=delimiter)
            for idx, row in enumerate(reader):
                cleaned_row = {k.strip(): (v.strip() if v else None) for k, v in row.items() if k}
                if not any(cleaned_row.values()):
                    continue

                rec_id = cleaned_row.get("id") or cleaned_row.get("candidate_id") or f"REC-CSV-{idx+1}-{uuid.uuid4().hex[:4]}"
                valid_records.append(RawRecord(
                    record_id=str(rec_id),
                    source_id=source_id,
                    source_type="csv",
                    raw_data=cleaned_row
                ))

        except Exception as e:
            failures.append({
                "source_id": source_id,
                "error": f"CSV parse failure: {str(e)}",
                "file_path": file_path
            })

        return valid_records, failures

    def ingest_text_file(self, file_path: str, source_id: str) -> Tuple[List[RawRecord], List[Dict[str, Any]]]:
        valid_records = []
        failures = []

        try:
            content = self._read_file_text(file_path)

            # Support multi-resume text files separated by lines of === or --- or CANDIDATE:
            sections = re.split(r'\n\s*[-=]{3,}\s*\n|\n\s*CANDIDATE\s*#?\d*:\s*\n', content)
            
            for idx, sec in enumerate(sections):
                sec_str = sec.strip()
                if not sec_str:
                    continue

                parsed_fields = self._parse_unstructured_text(sec_str)
                if parsed_fields:
                    rec_id = f"REC-TXT-{idx+1}-{uuid.uuid4().hex[:4]}"
                    valid_records.append(RawRecord(
                        record_id=rec_id,
                        source_id=source_id,
                        source_type="text",
                        raw_data=parsed_fields
                    ))
                else:
                    failures.append({
                        "source_id": source_id,
                        "section_index": idx,
                        "error": "Could not extract candidate information from text section",
                        "preview": sec_str[:150]
                    })

        except Exception as e:
            failures.append({
                "source_id": source_id,
                "error": f"Text ingestion error: {str(e)}",
                "file_path": file_path
            })

        return valid_records, failures

    def _parse_unstructured_text(self, text: str) -> Dict[str, Any]:
        """Extracts field key-values and entities from raw text/resumes using regex patterns."""
        extracted = {}

        # 1. Email matching
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text, flags=re.ASCII)
        if email_match:
            extracted["email"] = email_match.group(0)

        # 2. Phone matching
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            extracted["phone"] = phone_match.group(0)

        # 3. Explicit Key-Value line pairs (e.g. "Name: Rahul Kumar", "Experience: 5 years")
        kv_pairs = re.findall(r'(?m)^([A-Za-z\s_]+):\s*(.+)$', text)
        for key, val in kv_pairs:
            k_clean = key.strip().lower()
            v_clean = val.strip().rstrip('\ufffd\x00')
            if k_clean and v_clean:
                if k_clean == "email" and "email" in extracted:
                    continue  # Keep cleanly matched regex email
                extracted[k_clean] = v_clean

        # 4. Infer name if not explicitly set via key-value
        if "name" not in extracted and "full_name" not in extracted:
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            for line in lines[:3]:
                if not any(token in line.lower() for token in ["resume", "curriculum", "email", "phone", "http", "@", ":"]):
                    if len(line.split()) <= 4 and re.match(r'^[A-Za-z\s.\'-]+$', line):
                        extracted["candidate_name"] = line
                        break

        # 5. Extract skills list if present
        skills_match = re.search(r'(?:skills|technologies|competencies):\s*(.+)', text, re.IGNORECASE)
        if skills_match:
            raw_skills = skills_match.group(1)
            extracted["skills"] = [s.strip().rstrip('\ufffd\x00') for s in re.split(r'[,;|]', raw_skills) if s.strip()]

        # 6. Raw text preview as fallback metadata
        extracted["_raw_resume_text"] = text[:500]

        return extracted
