"""
Candidate Recommendation & AI Match Engine Unit Tests
"""

import unittest
from src.recommendation_engine import CandidateRecommendationEngine


class TestCandidateRecommendationEngine(unittest.TestCase):

    def setUp(self):
        self.engine = CandidateRecommendationEngine()

    def test_strong_match_candidate(self):
        sample_profile = {
            "candidate_id": "CAN-1001",
            "overall_confidence": 0.95,
            "profile": {
                "name": {"value": "Rahul Kumar"},
                "skills": {"value": ["Python", "Java", "SQL", "Docker"]},
                "experience_years": {"value": 5.0},
                "title": {"value": "Senior Software Engineer"}
            }
        }

        res = self.engine.evaluate_candidate_match(
            sample_profile,
            job_title="Senior Software Engineer",
            required_skills=["Python", "SQL", "Docker"],
            min_experience_years=3.0
        )

        self.assertEqual(res["suitability_level"], "Strong Match")
        self.assertGreaterEqual(res["match_score_pct"], 80.0)
        self.assertEqual(len(res["missing_skills"]), 0)

    def test_low_match_candidate(self):
        sample_profile = {
            "candidate_id": "CAN-1002",
            "overall_confidence": 0.80,
            "profile": {
                "name": {"value": "Priya Sharma"},
                "skills": {"value": ["HTML", "CSS"]},
                "experience_years": {"value": 0.5},
                "title": {"value": "Frontend Intern"}
            }
        }

        res = self.engine.evaluate_candidate_match(
            sample_profile,
            job_title="Data Scientist",
            required_skills=["Python", "Machine Learning", "SQL", "PyTorch"],
            min_experience_years=4.0
        )

        self.assertEqual(res["suitability_level"], "Low Match")
        self.assertLess(res["match_score_pct"], 60.0)
        self.assertIn("Python", res["missing_skills"])


if __name__ == "__main__":
    unittest.main()
