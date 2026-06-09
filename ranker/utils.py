import logging
import functools
import time
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import csv
import re

REQUIRED_SUBMISSION_HEADER = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")

def setup_logger(name: str) -> logging.Logger:
    """Setup a standardized logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_logger(__name__)

@dataclass
class CandidateProfile:
    """Validated candidate profile structure"""
    candidate_id: str
    profile: Dict[str, Any]
    skills: List[Dict[str, Any]]
    career_history: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    certifications: List[Dict[str, Any]]
    redrob_signals: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CandidateProfile':
        try:
            return cls(
                candidate_id=data.get("candidate_id") or data.get("id", "UNKNOWN"),
                profile=data.get("profile", {}),
                skills=data.get("skills", []),
                career_history=data.get("career_history", []),
                education=data.get("education", []),
                certifications=data.get("certifications", []),
                redrob_signals=data.get("redrob_signals", {}),
            )
        except Exception as e:
            logger.error(f"Invalid candidate structure: {e}")
            raise ValueError(f"Invalid candidate data: {e}")

@dataclass
class ScoringConfig:
    """Centralized configuration for scoring"""
    baseline_date: datetime = None
    min_years_experience: float = 2.0
    ideal_years_min: float = 6.0
    ideal_years_max: float = 8.0
    pre_llm_cutoff_date: str = "2022-01-01"
    recent_ai_cutoff_date: str = "2023-01-01"
    honeypot_signal_threshold: int = 2
    consulting_firm_multiplier: float = 0.4
    recent_only_ai_multiplier: float = 0.85
    final_score_boost: float = 1.05
    final_score_floor: float = 3
    
    def __post_init__(self):
        if self.baseline_date is None:
            self.baseline_date = datetime(2026, 6, 1)

def timer(func):
    """Decorator to time function execution and log performance"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            elapsed = time.time() - start_time
            logger.debug(f"{func.__name__} completed in {elapsed:.3f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"{func.__name__} failed after {elapsed:.3f}s: {e}")
            raise
    return wrapper

def get_candidate_id(candidate: Dict[str, Any], default: str = "UNKNOWN") -> str:
    """Get candidate ID with fallback logic."""
    return candidate.get("candidate_id") or candidate.get("id", default)

def get_field_safe(obj: Dict, *keys, default=None):
    """Safely access nested dict fields with fallback."""
    current = obj
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
    return current if current is not None else default

def safe_score_candidate(
    candidate: Dict[str, Any],
    tfidf_similarity: float = 0.0,
    config: Optional[ScoringConfig] = None
) -> Optional[Dict[str, Any]]:
    """Safely score a candidate with error handling."""
    from ranker.scorer import compute_composite_score
    if config is None:
        config = ScoringConfig()
    try:
        profile = CandidateProfile.from_dict(candidate)
        result = compute_composite_score(candidate, tfidf_similarity=tfidf_similarity, config=config)
        return result
    except ValueError as e:
        logger.error(f"Invalid candidate data: {e}")
        return None
    except Exception as e:
        logger.error(f"Error scoring candidate: {e}", exc_info=True)
        return None

@timer
def score_candidates_with_recovery(
    candidates: List[Dict[str, Any]],
    tfidf_scores: Dict[int, float],
    config: Optional[ScoringConfig] = None,
    skip_invalid: bool = True
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """Score candidates with comprehensive error handling and recovery."""
    if config is None:
        config = ScoringConfig()
    
    scored = []
    errors = []
    
    for i, candidate in enumerate(candidates):
        try:
            tfidf = tfidf_scores.get(i, 0.0)
            result = safe_score_candidate(candidate, tfidf, config)
            
            if result is None:
                msg = f"Failed to score candidate {i}"
                if skip_invalid:
                    errors.append(msg)
                    continue
                else:
                    raise ValueError(msg)
            
            scored.append({
                "candidate": candidate,
                "result": result,
                "composite": result.get("composite", 0),
                "candidate_id": get_candidate_id(candidate, default=f"UNKNOWN_{i}"),
            })
        except Exception as e:
            msg = f"Candidate {i}: {e}"
            if skip_invalid:
                errors.append(msg)
            else:
                raise
    
    logger.info(f"Scored {len(scored)}/{len(candidates)} candidates. Errors: {len(errors)}")
    return scored, errors

def validate_output_csv(
    csv_path: str,
    expected_rows: int = 100,
    strict_ranks: bool = True,
) -> bool:
    """Validate output CSV against the challenge submission rules."""
    errors = []
    try:
        with open(csv_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                logger.error("CSV validation failed: file is empty")
                return False

            if header != REQUIRED_SUBMISSION_HEADER:
                errors.append(
                    "header must be exactly "
                    f"{','.join(REQUIRED_SUBMISSION_HEADER)}"
                )

            rows = [row for row in reader if any(cell.strip() for cell in row)]

        if expected_rows is not None and len(rows) != expected_rows:
            errors.append(f"expected {expected_rows} data rows, found {len(rows)}")

        seen_ids = set()
        seen_ranks = set()
        by_rank = []

        for index, cells in enumerate(rows, start=2):
            if len(cells) != len(REQUIRED_SUBMISSION_HEADER):
                errors.append(
                    f"row {index}: expected {len(REQUIRED_SUBMISSION_HEADER)} "
                    f"columns, found {len(cells)}"
                )
                continue

            cid, rank_s, score_s, _reasoning = [cell.strip() for cell in cells]

            if not CANDIDATE_ID_PATTERN.match(cid):
                errors.append(f"row {index}: invalid candidate_id '{cid}'")
            elif cid in seen_ids:
                errors.append(f"row {index}: duplicate candidate_id '{cid}'")
            else:
                seen_ids.add(cid)

            try:
                rank = int(rank_s)
                if str(rank) != rank_s:
                    raise ValueError
                if rank < 1 or (expected_rows is not None and rank > expected_rows):
                    errors.append(f"row {index}: rank out of range '{rank_s}'")
                elif rank in seen_ranks:
                    errors.append(f"row {index}: duplicate rank {rank}")
                else:
                    seen_ranks.add(rank)
            except ValueError:
                errors.append(f"row {index}: rank must be an integer")
                rank = None

            try:
                score = float(score_s)
            except ValueError:
                errors.append(f"row {index}: score must be a float")
                score = None

            if rank is not None and score is not None and cid:
                by_rank.append((rank, score, cid))

        if strict_ranks and expected_rows is not None:
            expected = set(range(1, expected_rows + 1))
            missing = expected - seen_ranks
            if missing:
                errors.append(f"missing ranks: {sorted(missing)}")

        by_rank.sort(key=lambda x: x[0])
        for i in range(len(by_rank) - 1):
            r1, s1, _ = by_rank[i]
            r2, s2, _ = by_rank[i + 1]
            if s1 < s2:
                errors.append(
                    "score must be non-increasing by rank: "
                    f"rank {r1} ({s1}) < rank {r2} ({s2})"
                )

        for i in range(len(by_rank) - 1):
            r1, s1, c1 = by_rank[i]
            r2, s2, c2 = by_rank[i + 1]
            if s1 == s2 and c1 > c2:
                errors.append(
                    "equal score tie-break should use candidate_id ascending: "
                    f"rank {r1} {c1} > rank {r2} {c2}"
                )

        if errors:
            for error in errors[:20]:
                logger.error(f"CSV validation failed: {error}")
            if len(errors) > 20:
                logger.error(f"CSV validation failed: {len(errors) - 20} more issues")
            return False

        logger.info(f"CSV valid: {len(rows)} rows")
        return True
    except Exception as e:
        logger.error(f"Failed to validate CSV: {e}")
        return False
