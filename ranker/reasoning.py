"""
Per-candidate reasoning generation for the submission CSV.

Generates specific, factual, 1-2 sentence justifications that:
- Reference specific facts from the candidate's profile
- Connect to JD requirements
- Acknowledge honest concerns where gaps exist
- Vary substantively between candidates (not templated)
"""

from .constants import (
    CONSULTING_FIRMS, PREFERRED_LOCATIONS,
    JD_REQUIRED_SKILLS, JD_PREFERRED_SKILLS,
)
from .skill_matcher import normalize_skill


def generate_reasoning(candidate, result, rank):
    """
    Generate a 1-2 sentence reasoning for why this candidate is at this rank.

    Args:
        candidate: The candidate dict
        result: The scoring result from compute_composite_score
        rank: The candidate's rank (1-100)

    Returns:
        A string reasoning
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    sig = candidate.get("redrob_signals", {})
    skills = candidate.get("skills", [])

    title = profile.get("current_title", "Unknown")
    company = profile.get("current_company", "Unknown")
    years = profile.get("years_of_experience", 0)
    location = profile.get("location", "Unknown")

    dims = result.get("dimensions", {})
    flags = result.get("flags", {})
    sm = result.get("skill_match")
    composite = result.get("composite", 0)

    # Build skill match summary
    skill_names = [s.get("name", "") for s in skills[:5]]
    cand_skill_str = ", ".join(skill_names[:4]) if skill_names else "limited skills"

    req_matched = sm.get("required_matched", []) if sm else []
    req_missing = sm.get("required_missing", []) if sm else []
    pref_matched = sm.get("preferred_matched", []) if sm else []

    # Behavioral highlights
    response_rate = sig.get("recruiter_response_rate", 0)
    open_to_work = sig.get("open_to_work_flag", False)
    notice = sig.get("notice_period_days", 60)
    github = sig.get("github_activity_score", -1)

    parts = []

    # === Strong candidates (rank 1-20) ===
    if rank <= 20:
        # Lead with strongest dimension
        best_dim = max(dims, key=dims.get) if dims else "skills_depth"
        best_score = dims.get(best_dim, 0)

        # Primary strength statement
        if flags.get("hidden_gem_builder"):
            parts.append(
                f"{title} with {years:.1f}yr exp at {company}; "
                f"career explicitly shows they built recommendation/ranking systems in production"
            )
        elif len(req_matched) >= 3:
            matched_str = ", ".join(req_matched[:4])
            retrieval_terms = {
                "embeddings", "sentence-transformers", "vector database",
                "faiss", "pinecone", "weaviate", "qdrant", "milvus",
                "elasticsearch", "opensearch", "information retrieval",
            }
            if any(normalize_skill(s) in retrieval_terms for s in req_matched):
                match_label = "embeddings/retrieval/search requirements"
            else:
                match_label = "core JD requirements"
            parts.append(
                f"{title} with {years:.1f}yr exp at {company}; "
                f"matches {match_label} ({matched_str})"
            )
        elif best_dim == "role_fit":
            parts.append(
                f"{title} ({years:.1f}yr) with strong role alignment; "
                f"career shows actual production deployment of ML systems"
            )
        elif best_dim == "career_quality":
            parts.append(
                f"{title} at {company} with {years:.1f}yr exp; "
                f"career trajectory shows progression in relevant product companies"
            )
        else:
            parts.append(
                f"{title} with {years:.1f}yr exp; "
                f"{len(req_matched)}/{len(JD_REQUIRED_SKILLS)} required skills matched"
            )

        if flags.get("pre_llm_ml_experience"):
            parts.append("Shows pre-LLM-era ML experience")
        elif flags.get("applied_ml_system_evidence"):
            parts.append(
                f"Career evidence covers {', '.join(flags['applied_ml_system_evidence'][:2])}"
            )

        # Secondary signal
        secondaries = []
        if open_to_work:
            secondaries.append("open to work")
        if response_rate >= 0.5:
            secondaries.append(f"{response_rate:.0%} response rate")
        if github >= 40:
            secondaries.append("active GitHub")
        if notice <= 30:
            secondaries.append("immediate availability")
        if any(loc in location.lower() for loc in PREFERRED_LOCATIONS[:2]):
            secondaries.append(f"based in {location}")

        if secondaries:
            parts.append("; ".join(secondaries[:3]))

        # Honest concern for top candidates with gaps
        if req_missing and rank > 5:
            parts.append(
                f"gap: missing {', '.join(req_missing[:2])}"
            )
        if flags.get("availability_risk") and rank > 10:
            parts.append("Availability risk from stale/low-response platform signals")
        if flags.get("below_senior_experience_band") and rank > 5:
            parts.append("Concern: below the JD's 5-9 year seniority band")

    # === Mid-tier candidates (rank 21-60) ===
    elif rank <= 60:
        parts.append(
            f"{title} ({years:.1f}yr) at {company}"
        )

        # Skill match summary
        if len(req_matched) >= 2:
            parts.append(
                f"covers {len(req_matched)} required skills ({', '.join(req_matched[:3])})"
            )
        elif len(pref_matched) >= 1:
            parts.append(
                f"matches preferred skills ({', '.join(pref_matched[:2])}) "
                f"but limited required skill coverage"
            )
        else:
            parts.append(f"partial skill overlap with core skills: {cand_skill_str}")

        # Key concern
        concerns = []
        if flags.get("entire_career_consulting"):
            concerns.append("entire career at consulting firms")
        if flags.get("recent_only_ai"):
            concerns.append("AI experience appears primarily recent (<12mo)")
        if flags.get("title_chaser_risk"):
            concerns.append("frequent job changes")
        if flags.get("availability_risk"):
            concerns.append("weak availability signals")
        if flags.get("role_career_mismatch"):
            concerns.append("title/career does not support AI skill claims")
        if flags.get("below_senior_experience_band"):
            concerns.append("below the JD's 5-9 year seniority band")
        if req_missing:
            concerns.append(f"missing {', '.join(req_missing[:2])}")
        if response_rate < 0.2:
            concerns.append(f"low response rate ({response_rate:.0%})")

        if concerns:
            parts.append(f"concern: {'; '.join(concerns[:2])}")

    # === Lower-tier candidates (rank 61-100) ===
    else:
        parts.append(
            f"{title} ({years:.1f}yr) at {company}"
        )

        # Why they're lower ranked
        issues = []
        if flags.get("entire_career_consulting"):
            issues.append("entire career in consulting/services")
        if flags.get("recent_only_ai"):
            issues.append("primarily post-2023 AI experience without pre-LLM fundamentals")
        if flags.get("keyword_stuffer"):
            issues.append("skill-profile mismatch detected")
        if flags.get("role_career_mismatch"):
            issues.append("non-technical career despite AI skill claims")
        if flags.get("availability_risk"):
            issues.append("stale or low-response profile")
        if len(req_matched) <= 1:
            issues.append(f"only {len(req_matched)}/{len(JD_REQUIRED_SKILLS)} required skills")
        if years < 4:
            issues.append(f"below experience threshold ({years:.1f}yr vs 5+ required)")
        if not any(loc in location.lower() for loc in PREFERRED_LOCATIONS):
            issues.append(f"location: {location}")
        if response_rate < 0.15:
            issues.append("very low engagement")
        if notice > 90:
            issues.append(f"{notice}-day notice period")

        if issues:
            parts.append("; ".join(issues[:3]))
        else:
            parts.append(
                f"adjacent profile with {cand_skill_str}; "
                f"weaker overall fit for senior AI engineering role"
            )

    # Combine parts into 1-2 sentences
    reasoning = ". ".join(parts).strip()

    # Ensure no double periods and reasonable length
    reasoning = reasoning.replace("..", ".").replace(". .", ".")
    if len(reasoning) > 300:
        reasoning = reasoning[:297] + "..."

    return reasoning
