"""
JSON Schema Validation Module
Validates canonical JSON candidate profiles against runtime configurable JSON schemas.
"""

import json
import os
import re
from typing import Dict, Any, List, Tuple


class SchemaValidator:
    """Validates candidate JSON output profiles against schema requirements."""

    def __init__(self, schema_path: str):
        self.schema_path = schema_path
        self.schema = {}
        self.load_schema(schema_path)

    def load_schema(self, schema_path: str):
        if not os.path.exists(schema_path):
            raise FileNotFoundError(f"JSON schema file not found at: {schema_path}")

        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)

    def validate_profile(self, profile_dict: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a canonical candidate profile dictionary.
        Returns:
            (is_valid, list_of_error_messages)
        """
        errors = []

        # Try using jsonschema package if available in python environment
        try:
            import jsonschema
            jsonschema.validate(instance=profile_dict, schema=self.schema)
            return True, []
        except ImportError:
            # Fallback: Built-in schema validator using python stdlib
            return self._builtin_validate(profile_dict)
        except Exception as e:
            errors.append(f"Schema Validation Error: {str(e)}")
            return False, errors

    def _builtin_validate(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Built-in standard library schema validator fallback."""
        errors = []

        # Check required root fields
        required_fields = self.schema.get("required", ["candidate_id", "overall_confidence", "merged_sources", "profile"])
        for req in required_fields:
            if req not in data:
                errors.append(f"Missing required root property: '{req}'")

        if "candidate_id" in data:
            if not isinstance(data["candidate_id"], str) or not data["candidate_id"].startswith("CAN-"):
                errors.append(f"Invalid candidate_id format: '{data.get('candidate_id')}' (expected CAN-XXXXXXXX)")

        if "overall_confidence" in data:
            conf = data["overall_confidence"]
            if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
                errors.append(f"overall_confidence must be a float between 0.0 and 1.0, got: {conf}")

        if "merged_sources" in data and not isinstance(data["merged_sources"], list):
            errors.append("merged_sources must be a list of strings")

        if "profile" in data:
            prof = data["profile"]
            if not isinstance(prof, dict):
                errors.append("profile property must be an object")
            else:
                # Check email pattern if present
                if "email" in prof and isinstance(prof["email"], dict):
                    email_val = prof["email"].get("value")
                    if email_val and not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', str(email_val)):
                        errors.append(f"Invalid email format in profile: '{email_val}'")

                # Check experience_years numericality
                if "experience_years" in prof and isinstance(prof["experience_years"], dict):
                    exp_val = prof["experience_years"].get("value")
                    if exp_val is not None and not isinstance(exp_val, (int, float)):
                        errors.append(f"experience_years value must be numeric, got: {exp_val}")

                # Check skills array
                if "skills" in prof and isinstance(prof["skills"], dict):
                    skills_val = prof["skills"].get("value")
                    if skills_val is not None and not isinstance(skills_val, list):
                        errors.append("skills value must be a list of strings")

        is_valid = len(errors) == 0
        return is_valid, errors

    def validate_all_profiles(self, profiles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validates a batch of canonical profiles and produces a validation summary report."""
        total = len(profiles)
        valid_count = 0
        invalid_count = 0
        details = []

        for idx, prof in enumerate(profiles):
            is_valid, errors = self.validate_profile(prof)
            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1
                details.append({
                    "index": idx,
                    "candidate_id": prof.get("candidate_id", "UNKNOWN"),
                    "errors": errors
                })

        return {
            "total_validated": total,
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "pass_rate_pct": round((valid_count / total * 100) if total > 0 else 100.0, 2),
            "errors": details
        }
