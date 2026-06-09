#!/usr/bin/env python3
"""Validate a challenge submission CSV before upload."""

import argparse
import csv
import gzip
import json
import re
import sys
from pathlib import Path

REQUIRED_HEADER = ["candidate_id", "rank", "score", "reasoning"]
CANDIDATE_ID_PATTERN = re.compile(r"^CAND_[0-9]{7}$")
EXPECTED_ROWS = 100


def load_candidate_ids(path):
    if path is None:
        return None

    candidate_ids = set()
    source = Path(path)
    opener = gzip.open if source.suffix == ".gz" else open

    with opener(source, "rt", encoding="utf-8") as f:
        if source.suffix == ".json":
            data = json.load(f)
            for candidate in data:
                cid = candidate.get("candidate_id") or candidate.get("id")
                if cid:
                    candidate_ids.add(cid)
        else:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                candidate = json.loads(line)
                cid = candidate.get("candidate_id") or candidate.get("id")
                if cid:
                    candidate_ids.add(cid)

    return candidate_ids


def validate_submission(csv_path, candidates_path=None):
    errors = []
    path = Path(csv_path)
    valid_candidate_ids = load_candidate_ids(candidates_path)

    if path.suffix.lower() != ".csv":
        errors.append("Filename must use a .csv extension.")
    elif not path.stem:
        errors.append("Filename must be your registered participant ID.")

    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return ["Row 1 must be the header row; file is empty."]

            if header != REQUIRED_HEADER:
                errors.append(
                    "Header must be exactly: " + ",".join(REQUIRED_HEADER)
                )

            data_rows = [row for row in reader if any(cell.strip() for cell in row)]
    except UnicodeDecodeError:
        return ["File must be UTF-8 encoded."]
    except OSError as exc:
        return [f"Cannot read file: {exc}"]

    if len(data_rows) != EXPECTED_ROWS:
        errors.append(f"Expected exactly {EXPECTED_ROWS} data rows; found {len(data_rows)}.")

    seen_ids = set()
    seen_ranks = set()
    by_rank = []

    for offset, cells in enumerate(data_rows, start=2):
        if len(cells) != len(REQUIRED_HEADER):
            errors.append(f"Row {offset}: expected 4 columns; found {len(cells)}.")
            continue

        cid, rank_s, score_s, _reasoning = [cell.strip() for cell in cells]

        if not CANDIDATE_ID_PATTERN.match(cid):
            errors.append(f"Row {offset}: candidate_id must be CAND_XXXXXXX.")
        elif cid in seen_ids:
            errors.append(f"Row {offset}: duplicate candidate_id '{cid}'.")
        elif valid_candidate_ids is not None and cid not in valid_candidate_ids:
            errors.append(f"Row {offset}: candidate_id '{cid}' not found in candidates file.")
        else:
            seen_ids.add(cid)

        try:
            rank = int(rank_s)
            if str(rank) != rank_s:
                raise ValueError
            if not 1 <= rank <= EXPECTED_ROWS:
                errors.append(f"Row {offset}: rank must be between 1 and 100.")
            elif rank in seen_ranks:
                errors.append(f"Row {offset}: duplicate rank {rank}.")
            else:
                seen_ranks.add(rank)
        except ValueError:
            errors.append(f"Row {offset}: rank must be an integer.")
            rank = None

        try:
            score = float(score_s)
        except ValueError:
            errors.append(f"Row {offset}: score must be a float.")
            score = None

        if rank is not None and score is not None and cid:
            by_rank.append((rank, score, cid))

    missing = set(range(1, EXPECTED_ROWS + 1)) - seen_ranks
    if missing:
        errors.append(f"Each rank 1-100 must appear exactly once; missing: {sorted(missing)}.")

    by_rank.sort(key=lambda item: item[0])
    for i in range(len(by_rank) - 1):
        r1, s1, _ = by_rank[i]
        r2, s2, _ = by_rank[i + 1]
        if s1 < s2:
            errors.append(
                f"score must be non-increasing: rank {r1} ({s1}) < rank {r2} ({s2})."
            )

    for i in range(len(by_rank) - 1):
        r1, s1, c1 = by_rank[i]
        r2, s2, c2 = by_rank[i + 1]
        if s1 == s2 and c1 > c2:
            errors.append(
                f"Equal scores at ranks {r1} and {r2} should tie-break by candidate_id ascending."
            )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate challenge submission CSV.")
    parser.add_argument("csv_path")
    parser.add_argument("--candidates", help="Optional candidates.jsonl/json path.")
    args = parser.parse_args()

    errors = validate_submission(args.csv_path, args.candidates)
    if errors:
        print(f"Validation failed ({len(errors)} issue(s)):\n")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Submission is valid.")


if __name__ == "__main__":
    main()
