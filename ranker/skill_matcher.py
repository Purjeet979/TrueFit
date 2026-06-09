"""
Skill matching engine with alias resolution and ontology-based matching.
Handles the gap between what the JD asks for and how candidates describe their skills.
"""

import re
from .constants import SKILL_ALIASES, CORE_AI_SKILLS


def normalize_skill(name):
    """Normalize a skill name for comparison."""
    return name.lower().strip()


def build_alias_index():
    """
    Build a reverse lookup: for any alias or canonical name,
    return the canonical form and all its aliases.
    """
    index = {}
    for canonical, aliases in SKILL_ALIASES.items():
        canonical_norm = normalize_skill(canonical)
        all_forms = {canonical_norm} | {normalize_skill(a) for a in aliases}
        for form in all_forms:
            index[form] = (canonical_norm, all_forms)
    return index


# Module-level alias index (built once)
_ALIAS_INDEX = build_alias_index()


def get_canonical_skill(name):
    """Get the canonical form of a skill name."""
    norm = normalize_skill(name)
    if norm in _ALIAS_INDEX:
        return _ALIAS_INDEX[norm][0]
    return norm


def get_all_aliases(name):
    """Get all known aliases for a skill (including itself)."""
    norm = normalize_skill(name)
    if norm in _ALIAS_INDEX:
        return _ALIAS_INDEX[norm][1]
    return {norm}


def _build_skill_regex(alias):
    """Build a compiled regex for a skill alias."""
    if not alias:
        return None
    escaped = re.escape(alias)
    if re.match(r'^[a-z0-9]', alias):
        start = r'(?:^|[^a-z0-9._+#-])'
    else:
        start = r'(?:^|\s)'
    if re.search(r'[a-z0-9]$', alias):
        end = r'(?=$|[^a-z0-9._+#-])'
    else:
        end = r'(?=$|\s)'
    return re.compile(start + escaped + end, re.IGNORECASE)


# Pre-compile regex patterns for all known aliases
_SKILL_REGEX_CACHE = {}
for _canon, _data in _ALIAS_INDEX.items():
    _, _all_forms = _data
    for _form in _all_forms:
        if _form and _form not in _SKILL_REGEX_CACHE:
            _SKILL_REGEX_CACHE[_form] = _build_skill_regex(_form)


def skill_in_text(skill_name, text):
    """
    Check if a skill appears in a text body using word-boundary matching.
    Uses pre-compiled regex patterns for performance.
    """
    for alias in get_all_aliases(skill_name):
        if not alias:
            continue
        pattern = _SKILL_REGEX_CACHE.get(alias)
        if pattern is None:
            pattern = _build_skill_regex(alias)
            _SKILL_REGEX_CACHE[alias] = pattern
        if pattern and pattern.search(text):
            return True
    return False


def match_candidate_skills(candidate, required_skills, preferred_skills):
    """
    Match a candidate's skills against required and preferred skill lists.

    Returns dict with:
        - required_matched: list of matched required skills
        - required_missing: list of missing required skills
        - preferred_matched: list of matched preferred skills
        - required_ratio: fraction of required skills matched (0-1)
        - total_ratio: weighted match ratio
        - match_details: list of {skill, source, is_required} dicts
    """
    candidate_skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    profile = candidate.get("profile", {})

    # Build candidate skill name set (with aliases)
    cand_skill_set = set()
    for s in candidate_skills:
        name = normalize_skill(s.get("name", ""))
        cand_skill_set.add(name)
        cand_skill_set |= get_all_aliases(name)

    # Build evidence text from career history and profile
    career_text = " ".join(
        f"{j.get('title', '')} {j.get('description', '')} {j.get('industry', '')}"
        for j in career
    ).lower()

    profile_text = " ".join([
        profile.get("summary", ""),
        profile.get("headline", ""),
        profile.get("current_title", ""),
    ]).lower()

    full_text = f"{career_text} {profile_text}"

    def check_skill(skill_name):
        """Check a skill with cascading match strategies."""
        norm = normalize_skill(skill_name)
        all_aliases = get_all_aliases(skill_name)

        # Strategy 1: Direct skill profile match
        if all_aliases & cand_skill_set:
            matched_as = (all_aliases & cand_skill_set).pop()
            return "explicit", matched_as, 1.0

        # Strategy 2: Career history text match
        if skill_in_text(skill_name, career_text):
            return "career_history", skill_name, 0.75

        # Strategy 3: Profile/summary text match
        if skill_in_text(skill_name, profile_text):
            return "profile_text", skill_name, 0.5

        return "none", None, 0.0

    required_matched = []
    required_missing = []
    preferred_matched = []
    match_details = []

    # Check required skills
    for skill in required_skills:
        source, matched_as, credit = check_skill(skill)
        detail = {
            "skill": skill,
            "source": source,
            "matched_as": matched_as,
            "credit": credit,
            "is_required": True,
        }
        match_details.append(detail)
        if source != "none":
            required_matched.append(skill)
        else:
            required_missing.append(skill)

    # Check preferred skills
    for skill in preferred_skills:
        source, matched_as, credit = check_skill(skill)
        detail = {
            "skill": skill,
            "source": source,
            "matched_as": matched_as,
            "credit": credit,
            "is_required": False,
        }
        match_details.append(detail)
        if source != "none":
            preferred_matched.append(skill)

    # Compute ratios
    required_ratio = (
        len(required_matched) / len(required_skills)
        if required_skills else 0.5
    )

    # Weighted total ratio (required skills worth 2x)
    total_weight = len(required_skills) * 2 + len(preferred_skills)
    if total_weight > 0:
        matched_weight = sum(
            d["credit"] * (2.0 if d["is_required"] else 1.0)
            for d in match_details
        )
        total_ratio = matched_weight / total_weight
    else:
        total_ratio = 0.0

    return {
        "required_matched": required_matched,
        "required_missing": required_missing,
        "preferred_matched": preferred_matched,
        "required_ratio": required_ratio,
        "total_ratio": total_ratio,
        "match_details": match_details,
    }


def count_core_ai_skills(candidate):
    """
    Count how many core AI/ML skills a candidate has
    (from their explicit skill list only).
    """
    cand_skills = {
        normalize_skill(s.get("name", ""))
        for s in candidate.get("skills", [])
    }
    # Also expand via aliases
    expanded = set()
    for s in cand_skills:
        expanded.add(s)
        if s in _ALIAS_INDEX:
            expanded.add(_ALIAS_INDEX[s][0])  # add canonical form

    return len(expanded & {normalize_skill(s) for s in CORE_AI_SKILLS})


def get_skill_proficiency_score(candidate, target_skills):
    """
    Score based on proficiency levels for matched skills.
    Expert=100, Advanced=85, Intermediate=65, Beginner=40
    """
    prof_map = {
        "expert": 100, "advanced": 85,
        "intermediate": 65, "beginner": 40,
    }
    target_norms = set()
    for s in target_skills:
        target_norms |= get_all_aliases(s)

    scores = []
    for skill in candidate.get("skills", []):
        name = normalize_skill(skill.get("name", ""))
        if name in target_norms or get_canonical_skill(name) in target_norms:
            prof = skill.get("proficiency", "intermediate")
            scores.append(prof_map.get(prof, 50))

    return sum(scores) / len(scores) if scores else 40


def get_skill_endorsement_score(candidate, target_skills):
    """
    Average endorsement count for matched skills.
    Higher endorsements = more credible skill claims.
    """
    target_norms = set()
    for s in target_skills:
        target_norms |= get_all_aliases(s)

    endorsements = []
    for skill in candidate.get("skills", []):
        name = normalize_skill(skill.get("name", ""))
        if name in target_norms or get_canonical_skill(name) in target_norms:
            endorsements.append(skill.get("endorsements", 0))

    if not endorsements:
        return 0
    avg = sum(endorsements) / len(endorsements)
    # Normalize: 0 endorsements = 0, 50+ endorsements = 100
    return min(100, avg * 2)
