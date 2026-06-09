#!/usr/bin/env python3
"""
TrueFit Ranker — Intelligent Candidate Discovery & Ranking

Main entry point for producing the submission CSV.
Processes 100K candidates against the Redrob AI Senior AI Engineer JD
and outputs the top 100 ranked candidates.

Usage:
    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

Architecture:
    Stage 1: Load & parse candidate pool
    Stage 2: Hard pre-filters (eliminate obvious non-fits)
    Stage 3: Honeypot detection
    Stage 4: TF-IDF similarity (semantic pre-ranking)
    Stage 5: Multi-signal composite scoring
    Stage 6: Final ranking + reasoning generation
    Stage 7: CSV output

Constraints: ≤5 min CPU, ≤16 GB RAM, no GPU, no network.
"""

import argparse
import csv
import sys
import time
from datetime import datetime

from ranker.loader import load_candidates, extract_candidate_text
from ranker.honeypot import detect_honeypot
from ranker.tfidf import TFIDFCache
from ranker.reasoning import generate_reasoning
from ranker.constants import (
    JD_TEXT, STRONG_FIT_TITLE_KEYWORDS,
)
from ranker.skill_matcher import count_core_ai_skills
from ranker.utils import setup_logger, ScoringConfig, score_candidates_with_recovery, validate_output_csv

logger = setup_logger(__name__)

def parse_args():
    parser = argparse.ArgumentParser(
        description="TrueFit Ranker — Rank candidates for a job description"
    )
    parser.add_argument(
        "--candidates", "-c",
        required=True,
        help="Path to candidates.jsonl or candidates.jsonl.gz"
    )
    parser.add_argument(
        "--out", "-o",
        default="HaXker.csv",
        help="Output CSV path (default: HaXker.csv)"
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=100,
        help="Number of top candidates to output (default: 100)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress"
    )
    return parser.parse_args()


def hard_prefilter(candidates, verbose=False):
    """
    Stage 2: Eliminate candidates who are obviously not a fit.
    This reduces the pool before expensive scoring.
    """
    passed = []
    eliminated = {"no_experience": 0, "zero_skills": 0, "non_technical": 0}

    for c in candidates:
        profile = c.get("profile", {})
        years = profile.get("years_of_experience", 0)
        title = profile.get("current_title", "").lower()
        skills = c.get("skills", [])
        career = c.get("career_history", [])

        if years < 2:
            eliminated["no_experience"] += 1
            continue

        if len(skills) == 0 and len(career) == 0:
            eliminated["zero_skills"] += 1
            continue

        has_core_skill = count_core_ai_skills(c) >= 1
        has_tech_title = any(kw in title for kw in STRONG_FIT_TITLE_KEYWORDS)

        career_text = " ".join(
            j.get("description", "") for j in career
        ).lower()
        has_tech_career = any(
            kw in career_text
            for kw in ["python", "model", "data", "algorithm", "system",
                        "engineer", "develop", "deploy", "pipeline",
                        "machine learning", "ml", "software"]
        )

        if not has_core_skill and not has_tech_title and not has_tech_career:
            eliminated["non_technical"] += 1
            continue

        passed.append(c)

    if verbose:
        total_elim = sum(eliminated.values())
        logger.info(f"Pre-filter: {len(candidates):,} -> {len(passed):,} ({total_elim:,} eliminated)")
        for reason, count in eliminated.items():
            if count > 0:
                logger.info(f"  {reason}: {count:,}")

    return passed


def find_baseline_date(candidates):
    max_date = datetime(2026, 1, 1)
    for c in candidates:
        sig = c.get("redrob_signals", {})
        last_active = sig.get("last_active_date", "")
        if last_active:
            try:
                d = datetime.strptime(last_active[:10], "%Y-%m-%d")
                if d > max_date:
                    max_date = d
            except ValueError:
                pass
    return max_date


def main():
    args = parse_args()
    start_time = time.time()

    logger.info("=" * 60)
    logger.info("  TrueFit Ranker — Intelligent Candidate Discovery")
    logger.info("=" * 60)

    # ── Stage 1: Load candidates ──
    logger.info("[Stage 1/7] Loading candidates...")
    candidates = load_candidates(args.candidates)
    if not candidates:
        logger.error("Error: No candidates loaded.")
        sys.exit(1)

    baseline_date = find_baseline_date(candidates)
    logger.info(f"Baseline date: {baseline_date.strftime('%Y-%m-%d')}")
    config = ScoringConfig(baseline_date=baseline_date)

    # ── Stage 2: Hard pre-filters ──
    logger.info("[Stage 2/7] Applying hard pre-filters...")
    filtered = hard_prefilter(candidates, verbose=args.verbose)

    # ── Stage 3: Honeypot detection ──
    logger.info("[Stage 3/7] Detecting honeypots...")
    honeypots = []
    clean_candidates = []
    for c in filtered:
        is_hp, reasons = detect_honeypot(c)
        if is_hp:
            honeypots.append((c, reasons))
        else:
            clean_candidates.append(c)

    logger.info(f"Detected {len(honeypots)} honeypots, {len(clean_candidates):,} candidates remain")

    if args.verbose and honeypots:
        for c, reasons in honeypots[:5]:
            cid = c.get("candidate_id", "?")
            title = c.get("profile", {}).get("current_title", "?")
            logger.info(f"Honeypot: {cid} ({title}) - {'; '.join(reasons)}")

    # ── Stage 4: TF-IDF similarity ──
    logger.info("[Stage 4/7] Computing TF-IDF similarities...")
    t4_start = time.time()

    candidate_texts = []
    for i, c in enumerate(clean_candidates):
        text = extract_candidate_text(c)
        candidate_texts.append((i, text))

    tfidf_cache = TFIDFCache()
    tfidf_results = tfidf_cache.compute_with_caching(
        JD_TEXT, candidate_texts, top_k=min(2000, len(clean_candidates))
    )

    sim_map = {idx: sim for idx, sim in tfidf_results}

    t4_elapsed = time.time() - t4_start
    logger.info(f"TF-IDF computed in {t4_elapsed:.1f}s (top {len(tfidf_results)} candidates)")

    # ── Stage 5: Multi-signal scoring ──
    logger.info("[Stage 5/7] Scoring candidates (multi-signal)...")
    t5_start = time.time()

    scored, errors = score_candidates_with_recovery(
        clean_candidates, sim_map, config=config, skip_invalid=True
    )

    t5_elapsed = time.time() - t5_start
    logger.info(f"Scoring completed in {t5_elapsed:.1f}s ({len(scored):,} scored)")

    # ── Stage 6: Final ranking ──
    logger.info("[Stage 6/7] Ranking and generating reasoning...")

    scored.sort(key=lambda x: (-x["composite"], x["candidate_id"]))
    top_k = min(args.top_k, len(scored))
    if top_k < args.top_k:
        logger.error(
            f"Only {top_k} candidates available after filtering/scoring; "
            f"submission requires {args.top_k} rows."
        )
        sys.exit(1)
    top_candidates = scored[:top_k]
    max_composite = max((entry["composite"] for entry in top_candidates), default=1)
    if max_composite <= 0:
        max_composite = 1

    for rank_idx, entry in enumerate(top_candidates):
        reasoning = generate_reasoning(
            entry["candidate"],
            entry["result"],
            rank_idx + 1
        )
        entry["reasoning"] = reasoning
        entry["rank"] = rank_idx + 1
        entry["score"] = entry["composite"] / max_composite - rank_idx * 1e-7

    logger.info(f"Top {top_k} candidates ranked with reasoning")

    # ── Stage 7: Write CSV ──
    logger.info(f"[Stage 7/7] Writing output to {args.out}...")

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])

        for entry in top_candidates:
            writer.writerow([
                entry["candidate_id"],
                entry["rank"],
                f"{entry['score']:.6f}",
                entry["reasoning"],
            ])

    if validate_output_csv(args.out, expected_rows=top_k, strict_ranks=True):
        logger.info("CSV validation passed.")
    else:
        logger.warning("CSV validation failed.")
        sys.exit(1)

    # ── Summary ──
    total_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"  COMPLETE — {total_time:.1f}s total")
    logger.info("=" * 60)
    logger.info(f"Candidates loaded:  {len(candidates):>8,}")
    logger.info(f"After pre-filter:   {len(filtered):>8,}")
    logger.info(f"Honeypots detected: {len(honeypots):>8}")
    logger.info(f"Candidates scored:  {len(scored):>8,}")
    logger.info(f"Top candidates:     {top_k:>8}")

    if top_candidates:
        top = top_candidates[0]
        tc = top["candidate"]
        tp = tc.get("profile", {})
        logger.info("#1 Candidate:")
        logger.info(f"  ID:    {top['candidate_id']}")
        logger.info(f"  Name:  {tp.get('anonymized_name', '?')}")
        logger.info(f"  Title: {tp.get('current_title', '?')}")
        logger.info(f"  Exp:   {tp.get('years_of_experience', 0):.1f} years")
        logger.info(f"  Score: {top['score']:.4f}")

    logger.info(f"Output written to: {args.out}")
    logger.info(f"Runtime: {total_time:.1f}s (limit: 300s)")

if __name__ == "__main__":
    main()
