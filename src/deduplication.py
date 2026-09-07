"""
Deduplication Engine Module
Identifies duplicate candidate records using exact matching and multi-attribute weighted similarity scoring.
"""

import json
import os
from typing import List, Dict, Any, Tuple
from src.models import DuplicateMatch


def jaro_winkler_similarity(s1: str, s2: str, prefix_weight: float = 0.1) -> float:
    """
    Computes Jaro-Winkler similarity between two strings (0.0 to 1.0).
    Pure Python standard library implementation.
    """
    if not s1 or not s2:
        return 0.0
    if s1 == s2:
        return 1.0

    len1, len2 = len(s1), len(s2)
    max_dist = max(len1, len2) // 2 - 1
    if max_dist < 0:
        max_dist = 0

    s1_matches = [False] * len1
    s2_matches = [False] * len2

    matches = 0
    for i in range(len1):
        start = max(0, i - max_dist)
        end = min(i + max_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j]:
                continue
            if s1[i] == s2[j]:
                s1_matches[i] = True
                s2_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    transpositions = 0
    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    jaro = (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3.0

    # Winkler prefix scale
    prefix = 0
    for i in range(min(len1, len2, 4)):
        if s1[i] == s2[i]:
            prefix += 1
        else:
            break

    return jaro + prefix * prefix_weight * (1.0 - jaro)


def jaccard_similarity(set1: List[str], set2: List[str]) -> float:
    """Computes Jaccard index between two skill sets or string lists."""
    if not set1 or not set2:
        return 0.0
    s1, s2 = set(set1), set(set2)
    intersection = len(s1.intersection(s2))
    union = len(s1.union(s2))
    return intersection / float(union) if union > 0 else 0.0


class DeduplicationEngine:
    """Engine for identifying duplicate records across heterogeneous candidates."""

    def __init__(self, rules_config_path: str):
        self.rules_config_path = rules_config_path
        self.threshold_dup = 0.85
        self.threshold_possible = 0.65
        self.weights = {
            "email": 0.45,
            "phone": 0.30,
            "name": 0.15,
            "location": 0.05,
            "experience_years": 0.05
        }
        self.exact_overrides = {"email": True, "phone": True}
        self.load_config(rules_config_path)

    def load_config(self, config_path: str):
        if not os.path.exists(config_path):
            return  # Use default parameters if config not found

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        thresholds = data.get("thresholds", {})
        self.threshold_dup = thresholds.get("duplicate", 0.85)
        self.threshold_possible = thresholds.get("possible_match", 0.65)
        self.weights = data.get("attribute_weights", self.weights)
        self.exact_overrides = data.get("exact_match_override", self.exact_overrides)

    def compare_records(self, rec1: Dict[str, Any], rec2: Dict[str, Any]) -> DuplicateMatch:
        """
        Compares two normalized candidate dicts and evaluates similarity score.
        """
        attr_scores = {}
        id1 = rec1.get("record_id") or rec1.get("candidate_id", "rec1")
        id2 = rec2.get("record_id") or rec2.get("candidate_id", "rec2")

        # 1. Email Comparison
        e1 = rec1.get("email")
        e2 = rec2.get("email")
        if e1 and e2:
            email_sim = 1.0 if e1.lower() == e2.lower() else 0.0
            attr_scores["email"] = email_sim

            # Exact match override check
            if email_sim == 1.0 and self.exact_overrides.get("email"):
                return DuplicateMatch(
                    record_id_1=id1,
                    record_id_2=id2,
                    similarity_score=1.0,
                    matching_attributes={"email": 1.0},
                    status="DUPLICATE",
                    explanation=f"Exact email match override ({e1})"
                )

        # 2. Phone Comparison
        p1 = rec1.get("phone")
        p2 = rec2.get("phone")
        if p1 and p2:
            phone_sim = 1.0 if p1 == p2 else 0.0
            attr_scores["phone"] = phone_sim

            if phone_sim == 1.0 and self.exact_overrides.get("phone"):
                return DuplicateMatch(
                    record_id_1=id1,
                    record_id_2=id2,
                    similarity_score=0.98,
                    matching_attributes={"phone": 1.0},
                    status="DUPLICATE",
                    explanation=f"Exact phone match override ({p1})"
                )

        # 3. Name Comparison (Jaro-Winkler)
        n1 = rec1.get("name")
        n2 = rec2.get("name")
        if n1 and n2:
            name_sim = jaro_winkler_similarity(n1.lower(), n2.lower())
            attr_scores["name"] = name_sim

        # 4. Location Comparison
        loc1 = rec1.get("location")
        loc2 = rec2.get("location")
        if loc1 and loc2:
            attr_scores["location"] = jaro_winkler_similarity(loc1.lower(), loc2.lower())

        # 5. Experience Comparison
        exp1 = rec1.get("experience_years")
        exp2 = rec2.get("experience_years")
        if exp1 is not None and exp2 is not None:
            diff = abs(float(exp1) - float(exp2))
            attr_scores["experience_years"] = max(0.0, 1.0 - (diff / 5.0))

        # Calculate weighted similarity total
        total_weight = 0.0
        weighted_sum = 0.0

        for attr, weight in self.weights.items():
            if attr in attr_scores:
                weighted_sum += attr_scores[attr] * weight
                total_weight += weight

        final_score = (weighted_sum / total_weight) if total_weight > 0 else 0.0

        # Determine status
        if final_score >= self.threshold_dup:
            status = "DUPLICATE"
            explanation = f"High similarity score ({final_score:.2f} >= {self.threshold_dup})"
        elif final_score >= self.threshold_possible:
            status = "POSSIBLE_MATCH"
            explanation = f"Moderate similarity score ({final_score:.2f} >= {self.threshold_possible}), flagged for review"
        else:
            status = "UNIQUE"
            explanation = f"Distinct candidate profiles ({final_score:.2f} < {self.threshold_possible})"

        return DuplicateMatch(
            record_id_1=id1,
            record_id_2=id2,
            similarity_score=final_score,
            matching_attributes=attr_scores,
            status=status,
            explanation=explanation
        )

    def _generate_blocking_keys(self, rec: Dict[str, Any]) -> List[str]:
        """Generates tight, highly selective blocking indexing keys for O(N) deduplication."""
        keys = []
        email = rec.get("email")
        if email and isinstance(email, str) and email.strip():
            clean_email = email.strip().lower()
            if clean_email.startswith("mailto:"):
                clean_email = clean_email[7:]
            keys.append(f"email:{clean_email}")

        phone = rec.get("phone")
        if phone and isinstance(phone, str) and phone.strip():
            digits = "".join(ch for ch in phone if ch.isdigit())
            if len(digits) >= 7:
                keys.append(f"phone:{digits[-10:]}")

        name = rec.get("name")
        if name and isinstance(name, str) and name.strip():
            tokens = [t.lower() for t in name.strip().split() if t.isalpha()]
            if len(tokens) >= 2:
                # Full name key (e.g. rahul_kumar)
                keys.append(f"name_full:{tokens[0]}_{tokens[-1]}")
            elif len(tokens) == 1 and len(tokens[0]) >= 3:
                keys.append(f"name_single:{tokens[0]}")

        return keys

    def find_all_duplicates(
        self,
        records: List[Dict[str, Any]],
        use_blocking: bool = True
    ) -> Tuple[List[List[int]], List[DuplicateMatch]]:
        """
        Compares candidate record pairs to find duplicates and clusters.
        Uses candidate blocking/indexing when use_blocking=True or len(records) > 50 to scale efficiently to 10,000+ records.
        Returns:
            (clusters_of_duplicate_record_indices, list_of_all_duplicate_matches)
        """
        n = len(records)
        duplicate_matches = []
        adj = {i: set() for i in range(n)}

        # Determine candidate pairs to compare
        if use_blocking and n > 50:
            blocks: Dict[str, List[int]] = {}
            for idx, rec in enumerate(records):
                keys = self._generate_blocking_keys(rec)
                for k in keys:
                    if k not in blocks:
                        blocks[k] = []
                    blocks[k].append(idx)

            pairs_to_check = set()
            for key, indices in blocks.items():
                if len(indices) > 1:
                    for x in range(len(indices)):
                        for y in range(x + 1, len(indices)):
                            i, j = indices[x], indices[y]
                            if i > j:
                                i, j = j, i
                            pairs_to_check.add((i, j))
        else:
            pairs_to_check = {(i, j) for i in range(n) for j in range(i + 1, n)}

        # Compare candidate pairs
        for i, j in pairs_to_check:
            match = self.compare_records(records[i], records[j])
            if match.status in ["DUPLICATE", "POSSIBLE_MATCH"]:
                duplicate_matches.append(match)

            if match.status == "DUPLICATE":
                adj[i].add(j)
                adj[j].add(i)

        # Connected components (clusters)
        visited = set()
        clusters = []

        for i in range(n):
            if i not in visited:
                cluster = []
                queue = [i]
                visited.add(i)
                while queue:
                    curr = queue.pop(0)
                    cluster.append(curr)
                    for neighbor in adj[curr]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            queue.append(neighbor)
                clusters.append(cluster)

        return clusters, duplicate_matches
