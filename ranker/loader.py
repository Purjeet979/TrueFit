"""
Data loading and parsing for candidates.jsonl.
Handles both raw JSONL and gzipped JSONL files.
"""

import json
import gzip
import sys
from pathlib import Path
from .utils import setup_logger

logger = setup_logger(__name__)


def load_candidates(filepath):
    """
    Load candidates from a JSONL or JSONL.GZ file.
    Returns a list of candidate dicts.
    """
    path = Path(filepath)

    if not path.exists():
        logger.error(f"Error: File not found: {filepath}")
        sys.exit(1)

    if path.suffix == ".json":
        return load_json_candidates(filepath)

    candidates = []
    opener = gzip.open if path.suffix == ".gz" else open

    logger.info(f"Loading candidates from {path.name}...")

    with opener(path, "rt", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                candidate = json.loads(line)
                candidates.append(candidate)
            except json.JSONDecodeError as e:
                logger.warning(f"Skipping malformed line {line_num}: {e}")

    logger.info(f"Loaded {len(candidates):,} candidates.")
    return candidates


def load_json_candidates(filepath):
    """
    Load candidates from a JSON array file (e.g., sample_candidates.json).
    """
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    logger.info(f"Loaded {len(candidates):,} candidates from JSON.")
    return candidates


def extract_candidate_text(candidate):
    """
    Build a single searchable text string from all candidate fields.
    Used for TF-IDF and keyword matching.
    """
    parts = []

    profile = candidate.get("profile", {})
    parts.append(profile.get("summary", ""))
    parts.append(profile.get("headline", ""))
    parts.append(profile.get("current_title", ""))
    parts.append(profile.get("current_industry", ""))

    # Skills — weighted (appear multiple times for TF-IDF boost)
    for skill in candidate.get("skills", []):
        name = skill.get("name", "")
        parts.append(name)
        parts.append(name)  # double-weight skills in search text

    # Career history — titles, descriptions, industries
    for job in candidate.get("career_history", []):
        parts.append(job.get("title", ""))
        parts.append(job.get("industry", ""))
        parts.append(job.get("description", ""))

    # Education
    for edu in candidate.get("education", []):
        parts.append(edu.get("degree", ""))
        parts.append(edu.get("field_of_study", ""))

    # Certifications
    for cert in candidate.get("certifications", []):
        parts.append(cert.get("name", ""))

    return " ".join(parts).lower()
