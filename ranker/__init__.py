# TrueFit Ranker — Intelligent Candidate Discovery & Ranking Engine

__version__ = "1.0.0"
__author__ = "Purjeet"

from .loader import load_candidates, extract_candidate_text
from .honeypot import detect_honeypot, detect_keyword_stuffer
from .tfidf import compute_tfidf_similarity
from .scorer import compute_composite_score
from .reasoning import generate_reasoning
from .skill_matcher import match_candidate_skills, count_core_ai_skills
from .constants import SCORING_WEIGHTS, JD_TEXT

__all__ = [
    "load_candidates",
    "extract_candidate_text",
    "detect_honeypot",
    "detect_keyword_stuffer",
    "compute_tfidf_similarity",
    "compute_composite_score",
    "generate_reasoning",
    "match_candidate_skills",
    "count_core_ai_skills",
    "SCORING_WEIGHTS",
    "JD_TEXT",
]