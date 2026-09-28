"""
AI-Assisted Candidate Recommendation & Match Scoring Engine
Evaluates candidate profiles against target job requirements, computing skill overlap, experience alignment, and overall suitability scores (0-100%).
"""

from typing import Dict, Any, List


class CandidateRecommendationEngine:
    """Computes explainable candidate suitability scores and skill match analytics."""

    def __init__(self):
        pass

    def evaluate_candidate_match(
        self,
        profile_dict: Dict[str, Any],
        job_title: str = "Senior Software Engineer",
        required_skills: List[str] = None,
        min_experience_years: float = 2.0
    ) -> Dict[str, Any]:
        """
        Evaluates a canonical profile dictionary against target job criteria.
        Returns match score (0-100), suitability category, matched/missing skills, and detailed rationale.
        """
        if required_skills is None:
            required_skills = ["Python", "Java", "SQL", "Docker", "AWS"]

        prof = profile_dict.get("profile", {})
        cand_name = prof.get("name", {}).get("value", "Unnamed Candidate") if prof.get("name") else "Unnamed Candidate"
        cand_skills = prof.get("skills", {}).get("value", []) if prof.get("skills") else []
        cand_exp = prof.get("experience_years", {}).get("value", 0.0) if prof.get("experience_years") else 0.0
        cand_title = prof.get("title", {}).get("value", "") if prof.get("title") else ""

        # 1. Skill Match Scoring (Weight: 50%)
        req_set = {s.lower() for s in required_skills}
        cand_set = {s.lower() for s in cand_skills} if isinstance(cand_skills, list) else set()

        matched_skills_lower = req_set.intersection(cand_set)
        missing_skills_lower = req_set - cand_set

        matched_skills = [s for s in required_skills if s.lower() in matched_skills_lower]
        missing_skills = [s for s in required_skills if s.lower() in missing_skills_lower]

        skill_match_ratio = (len(matched_skills) / len(required_skills)) if required_skills else 1.0
        skill_score = skill_match_ratio * 50.0

        # 2. Experience Alignment Scoring (Weight: 30%)
        try:
            exp_val = float(cand_exp) if cand_exp is not None else 0.0
        except (ValueError, TypeError):
            exp_val = 0.0

        if exp_val >= min_experience_years:
            exp_score = 30.0
        else:
            exp_score = (exp_val / min_experience_years) * 30.0 if min_experience_years > 0 else 30.0

        # 3. Title & Confidence Alignment Scoring (Weight: 20%)
        title_match = 10.0 if any(token in cand_title.lower() for token in job_title.lower().split()) else 5.0
        conf_boost = profile_dict.get("overall_confidence", 0.9) * 10.0
        title_score = title_match + conf_boost

        total_match_score = round(min(100.0, max(0.0, skill_score + exp_score + title_score)), 1)

        # Suitability Category
        if total_match_score >= 80.0:
            suitability = "Strong Match"
        elif total_match_score >= 60.0:
            suitability = "Moderate Match"
        else:
            suitability = "Low Match"

        explanation = (
            f"Candidate '{cand_name}' achieved a {total_match_score}% match for '{job_title}'. "
            f"Matched {len(matched_skills)}/{len(required_skills)} required skills. "
            f"Experience: {exp_val} years (Required: {min_experience_years} years)."
        )

        return {
            "candidate_id": profile_dict.get("candidate_id", "UNKNOWN"),
            "candidate_name": cand_name,
            "target_job_title": job_title,
            "match_score_pct": total_match_score,
            "suitability_level": suitability,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "candidate_experience_years": exp_val,
            "required_experience_years": min_experience_years,
            "explanation": explanation
        }
