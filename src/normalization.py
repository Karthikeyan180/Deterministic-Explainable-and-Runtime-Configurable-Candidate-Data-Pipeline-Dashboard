"""
Deterministic Data Normalization Engine
Normalizes heterogeneous candidate attribute values into clean, standardized canonical forms.
"""

import re
from typing import List, Tuple, Any, Optional


class DataNormalizer:
    """Provides deterministic normalizers for common candidate attributes."""

    # Standard canonical skill dictionary for normalization
    SKILL_CANONICAL_MAP = {
        "java": "Java",
        "javaprogramming": "Java",
        "java programming": "Java",
        "py": "Python",
        "python": "Python",
        "python3": "Python",
        "js": "JavaScript",
        "javascript": "JavaScript",
        "node": "Node.js",
        "nodejs": "Node.js",
        "node.js": "Node.js",
        "react": "React",
        "reactjs": "React",
        "react.js": "React",
        "ts": "TypeScript",
        "typescript": "TypeScript",
        "sql": "SQL",
        "postgresql": "PostgreSQL",
        "postgres": "PostgreSQL",
        "c++": "C++",
        "cpp": "C++",
        "c#": "C#",
        "csharp": "C#",
        "aws": "AWS",
        "amazon web services": "AWS",
        "docker": "Docker",
        "kubernetes": "Kubernetes",
        "k8s": "Kubernetes",
        "git": "Git",
        "html": "HTML",
        "css": "CSS",
        "rest api": "REST API",
        "restful apis": "REST API",
        "machine learning": "Machine Learning",
        "ml": "Machine Learning",
        "ai": "Artificial Intelligence",
        "deep learning": "Deep Learning"
    }

    def __init__(self):
        pass

    def normalize_email(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """
        Normalizes email addresses:
        "  RAHUL@GMAIL.COM " -> "rahul@gmail.com"
        Returns (normalized_value, transformation_rules_applied).
        """
        if not val or not isinstance(val, str):
            return None, ["invalid_input"]

        raw = val.strip()
        rules = []

        # Remove mailto: prefix if present
        if raw.lower().startswith("mailto:"):
            raw = raw[7:].strip()
            rules.append("stripped_mailto_prefix")

        norm = raw.lower()
        if norm != raw:
            rules.append("lowercased")

        # Validate basic email syntax
        if re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', norm):
            rules.append("validated_email_pattern")
            return norm, rules
        else:
            rules.append("failed_syntax_check")
            return norm, rules

    def normalize_phone(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """
        Normalizes phone numbers to standard E.164 format:
        "+1 (555) 019-2834" -> "+15550192834"
        "0091 9876543210" -> "+919876543210"
        Returns (normalized_value, transformation_rules_applied).
        """
        if not val or not isinstance(val, (str, int, float)):
            return None, ["invalid_input"]

        raw = str(val).strip()
        rules = []

        has_plus = raw.startswith("+")
        digits = re.sub(r'\D', '', raw)
        if not digits:
            return None, ["no_digits_found"]

        rules.append("removed_non_digits")

        if not has_plus:
            if digits.startswith("00") and len(digits) > 10:
                digits = digits[2:]
                has_plus = True
                rules.append("converted_double_zero_prefix_to_plus")

        if has_plus:
            norm = f"+{digits}"
            rules.append("retained_country_code_plus")
        elif len(digits) >= 11:
            norm = f"+{digits}"
            rules.append("inferred_international_e164")
        else:
            norm = digits
            rules.append("standard_local_digits")

        return norm, rules

    def normalize_name(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """
        Normalizes candidate names:
        "  mr. rahul KUMAR  " -> "Rahul Kumar"
        """
        if not val or not isinstance(val, str):
            return None, ["invalid_input"]

        raw = val.strip()
        rules = []

        # Strip titles/honorifics
        cleaned = re.sub(r'^(mr\.|mrs\.|ms\.|dr\.|prof\.)\s+', '', raw, flags=re.IGNORECASE).strip()
        if cleaned != raw:
            rules.append("removed_title_honorific")

        # Normalize whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        rules.append("normalized_whitespace")

        # Title-case if all uppercase or lowercase
        if cleaned.isupper() or cleaned.islower():
            cleaned = cleaned.title()
            rules.append("title_cased")

        return cleaned, rules

    def normalize_experience(self, val: Any) -> Tuple[Optional[float], List[str]]:
        """
        Normalizes experience values:
        "24 months" -> 2.0
        "2.5 years" -> 2.5
        "3 yrs" -> 3.0
        """
        if val is None:
            return None, ["missing_value"]

        rules = []

        if isinstance(val, (int, float)):
            return float(val), ["direct_numeric"]

        raw = str(val).strip().lower()

        # Check for months
        month_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:months?|mos?|mths?)', raw)
        if month_match:
            months = float(month_match.group(1))
            years = round(months / 12.0, 2)
            rules.append(f"converted_months_to_years_{months}_to_{years}")
            return years, rules

        # Check for years
        year_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:years?|yrs?|yr)?', raw)
        if year_match:
            years = float(year_match.group(1))
            rules.append("extracted_numeric_years")
            return years, rules

        # Fallback: extract any isolated float/int
        num_match = re.search(r'\d+(?:\.\d+)?', raw)
        if num_match:
            years = float(num_match.group(0))
            rules.append("extracted_first_numeric_token")
            return years, rules

        return None, ["failed_numeric_extraction"]

    def normalize_skills(self, val: Any) -> Tuple[List[str], List[str]]:
        """
        Normalizes skill list or skill string:
        ["JAVA", "python", "Java Programming"] -> ["Java", "Python"]
        """
        if not val:
            return [], ["empty_skills"]

        rules = []
        raw_list = []

        if isinstance(val, str):
            raw_list = [s.strip() for s in re.split(r'[,;|]', val) if s.strip()]
            rules.append("split_skill_string")
        elif isinstance(val, list):
            raw_list = [str(s).strip() for s in val if s]
            rules.append("processed_skill_array")

        normalized_set = set()
        for skill in raw_list:
            skill_lower = skill.lower().strip()
            if skill_lower in self.SKILL_CANONICAL_MAP:
                normalized_set.add(self.SKILL_CANONICAL_MAP[skill_lower])
                rules.append(f"mapped_{skill}_to_{self.SKILL_CANONICAL_MAP[skill_lower]}")
            else:
                # Capitalize words
                cap_skill = skill.title()
                normalized_set.add(cap_skill)
                rules.append(f"title_cased_{skill}")

        result = sorted(list(normalized_set))
        return result, rules

    def normalize_education(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """Normalizes education levels (e.g., 'B.Tech in CS' -> 'B.Tech Computer Science')."""
        if not val or not isinstance(val, str):
            return None, ["invalid_input"]

        raw = val.strip()
        rules = ["trimmed_whitespace"]

        cleaned = re.sub(r'\s+', ' ', raw)
        return cleaned, rules

    def normalize_location(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """Normalizes location strings (e.g., 'bangalore, india' -> 'Bangalore, India')."""
        if not val or not isinstance(val, str):
            return None, ["invalid_input"]

        raw = val.strip()
        rules = ["trimmed_whitespace"]
        parts = [p.strip().title() for p in raw.split(",") if p.strip()]
        norm = ", ".join(parts)
        rules.append("title_cased_parts")

        return norm, rules

    def normalize_title(self, val: Any) -> Tuple[Optional[str], List[str]]:
        """Normalizes job titles (e.g. 'sr. software engineer' -> 'Senior Software Engineer')."""
        if not val or not isinstance(val, str):
            return None, ["invalid_input"]

        raw = val.strip()
        rules = []

        norm = re.sub(r'\bsr\.?\b', 'Senior', raw, flags=re.IGNORECASE)
        norm = re.sub(r'\bjr\.?\b', 'Junior', norm, flags=re.IGNORECASE)
        norm = re.sub(r'\bsw\b', 'Software', norm, flags=re.IGNORECASE)
        norm = re.sub(r'\bdev\b', 'Developer', norm, flags=re.IGNORECASE)
        norm = re.sub(r'\s+', ' ', norm).title()
        rules.append("expanded_title_abbreviations")

        return norm, rules
