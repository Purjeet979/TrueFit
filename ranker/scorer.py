"""
Multi-signal scoring engine for the TrueFit ranker.

Scores candidates across 5 dimensions tuned for the Redrob AI
Senior AI Engineer JD, with specific attention to:
- Title-career coherence (detecting keyword stuffers)
- Consulting firm career penalty
- Production experience detection
- Behavioral signal weighting
- Honeypot avoidance
"""

import math
import re
from datetime import datetime, timedelta

from .utils import setup_logger, ScoringConfig

logger = setup_logger(__name__)

from .constants import (
    SCORING_WEIGHTS, CONSULTING_FIRMS, NON_TECHNICAL_TITLES,
    STRONG_FIT_TITLES, STRONG_FIT_TITLE_KEYWORDS,
    WEAK_FIT_TITLE_KEYWORDS, SENIORITY_LEVELS,
    PRODUCTION_INDICATORS, ML_PRODUCTION_INDICATORS,
    LEADERSHIP_INDICATORS, PREFERRED_LOCATIONS, INDIA_LOCATIONS,
    JD_REQUIRED_SKILLS, JD_PREFERRED_SKILLS,
    CORE_AI_SKILLS, SHALLOW_AI_INDICATORS, FICTIONAL_COMPANIES,
)
from .skill_matcher import (
    match_candidate_skills, count_core_ai_skills,
    get_skill_proficiency_score, normalize_skill,
    get_skill_endorsement_score,
)
from .honeypot import detect_honeypot, detect_keyword_stuffer


def clamp(val, lo=0, hi=100):
    return max(lo, min(hi, val))


def _career_text(candidate):
    career = candidate.get("career_history", [])
    return " ".join(
        f"{j.get('title', '')} {j.get('industry', '')} {j.get('description', '')}"
        for j in career
    ).lower()


def _is_non_technical_profile(candidate):
    profile = candidate.get("profile", {})
    years = profile.get("years_of_experience", 0)
    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    title_text = f"{title} {headline}"
    return any(nt in title_text for nt in NON_TECHNICAL_TITLES)


def _is_cv_speech_specialist(candidate):
    """
    JD explicitly disqualifies: 'people whose primary expertise is computer
    vision, speech, or robotics without significant NLP/IR exposure.'
    """
    career_text = _career_text(candidate)
    skills = {s.get("name", "").lower() for s in candidate.get("skills", [])}

    cv_speech_terms = [
        "computer vision", "image classification", "object detection",
        "yolo", "opencv", "image segmentation", "speech recognition",
        "asr", "text to speech", "tts", "robotics", "ros ", "slam",
        "3d vision", "lidar", "point cloud", "pose estimation",
        "action recognition", "video understanding",
    ]
    nlp_ir_terms = [
        "nlp", "natural language", "text classification", "retrieval",
        "ranking", "embedding", "transformer", "bert", "language model",
        "information retrieval", "search", "recommendation", "rag",
    ]

    cv_count = sum(1 for t in cv_speech_terms if t in career_text)
    nlp_count = sum(1 for t in nlp_ir_terms if t in career_text)

    # Join all skill names once for O(n) check instead of O(n*m) nested loop
    skills_text = " ".join(skills)
    cv_skill_count = sum(1 for t in cv_speech_terms if t in skills_text)

    # CV/speech specialist = heavy CV signals but minimal NLP/IR
    return (cv_count + cv_skill_count) >= 3 and nlp_count <= 1


def _is_pure_researcher(candidate):
    """
    JD explicitly disqualifies: 'pure research environments (academic labs,
    research-only roles) without any production deployment.'
    """
    career = candidate.get("career_history", [])
    if not career:
        return False

    research_title_terms = [
        "research", "researcher", "scientist", "phd", "postdoc",
        "fellow", "lab", "professor", "lecturer", "academic",
    ]
    production_terms = [
        "production", "deployed", "shipped", "users", "scale",
        "api", "service", "pipeline", "realtime", "real-time",
        "inference", "serving", "microservice", "system",
    ]

    titles = [j.get("title", "").lower() for j in career]
    institutions = [j.get("company", "").lower() for j in career]
    descriptions = " ".join(j.get("description", "").lower() for j in career)

    research_title_count = sum(
        1 for t in titles if any(r in t for r in research_title_terms)
    )
    academic_company_count = sum(
        1 for inst in institutions
        if any(kw in inst for kw in ["university", "iit", "iim", "iisc",
                                     "mit", "stanford", "research lab",
                                     "institute", "college"])
    )
    has_production = any(p in descriptions for p in production_terms)

    total = len(career)
    return (
        (research_title_count >= total * 0.7 or academic_company_count >= total * 0.7)
        and not has_production
    )


def _has_recent_coding_evidence(candidate, baseline_date):
    """
    JD disqualifies: 'senior engineer who hasn't written production code
    in the last 18 months because they moved into architecture roles.'
    """
    career = candidate.get("career_history", [])
    if not career:
        return True  # Benefit of doubt

    current_job = career[0]
    end_date = current_job.get("end_date", "")
    cutoff = (baseline_date - timedelta(days=18 * 30)).strftime("%Y-%m-%d")

    if end_date and end_date < cutoff:
        return True  # Left long ago — not penalised

    title = current_job.get("title", "").lower()
    desc = current_job.get("description", "").lower()

    arch_signals = [
        "architecture", "solution architect", "tech lead",
        "head of engineering", "vp engineering", "director of engineering",
        "principal", "cto",
    ]
    coding_signals = [
        "code", "implement", "built", "develop", "python",
        "ship", "deploy", "debug", "pull request", "commit", "refactor",
    ]

    in_arch_role = any(a in title for a in arch_signals)
    has_coding_evidence = any(c in desc for c in coding_signals)

    return not (in_arch_role and not has_coding_evidence)


def _technical_career_depth(candidate):
    career_text = _career_text(candidate)
    indicators = [
        "python", "model", "training", "inference", "pipeline", "deploy",
        "algorithm", "neural", "embedding", "vector", "ml ", "machine learning",
        "deep learning", "nlp", "data science", "api", "backend", "software",
        "search", "ranking", "recommendation", "retrieval", "distributed",
    ]
    return sum(1 for ind in indicators if ind in career_text)


def _applied_ml_system_evidence(candidate):
    """
    Detect career evidence that implies the JD fit even when exact AI-tool
    keywords are absent from the skills list.
    """
    career_text = _career_text(candidate)
    families = {
        "recommendation": [
            "recommendation system", "recommender", "personalization",
            "collaborative filtering", "content-based", "user-item",
        ],
        "search_ranking": [
            "search system", "search relevance", "ranking system",
            "ranking model", "learning to rank", "query understanding",
            "candidate matching", "matching engine", "relevance",
        ],
        "retrieval": [
            "retrieval system", "information retrieval", "semantic search",
            "hybrid search", "hybrid retrieval", "vector search",
            "nearest neighbor", "ann search", "approximate nearest",
            "reciprocal rank fusion", "rrf", "dense retrieval",
            "sparse retrieval", "bm25",
        ],
        "production_ml": [
            "model serving", "model deployment", "inference", "ml pipeline",
            "training pipeline", "feature store", "a/b test", "experiment",
            "online model", "production model",
        ],
        "scale": [
            "millions of users", "million users", "100k", "1m", "latency",
            "throughput", "real-time", "realtime", "scaled",
        ],
    }

    matched = {
        family: [term for term in terms if term in career_text]
        for family, terms in families.items()
    }
    active_families = [family for family, terms in matched.items() if terms]

    score = 0
    if matched["recommendation"]:
        score += 4
    if matched["search_ranking"]:
        score += 4
    if matched["retrieval"]:
        score += 3
    if matched["production_ml"]:
        score += 3
    if matched["scale"]:
        score += 2

    return {
        "score": min(12, score),
        "families": active_families,
        "matched_terms": matched,
    }


def _availability_flags(candidate, baseline_date):
    sig = candidate.get("redrob_signals", {})
    flags = {}

    last_active = sig.get("last_active_date", "")
    days_since_active = None
    if last_active:
        try:
            active_date = datetime.strptime(last_active[:10], "%Y-%m-%d")
            days_since_active = max(0, (baseline_date - active_date).days)
        except ValueError:
            pass

    response_rate = sig.get("recruiter_response_rate", 0)
    if days_since_active is not None:
        flags["days_since_active"] = days_since_active
        flags["stale_profile"] = days_since_active > 180
        flags["inactive_90d"] = days_since_active > 90
    flags["very_low_response"] = response_rate < 0.10
    flags["low_response"] = response_rate < 0.20
    flags["not_open_to_work"] = not sig.get("open_to_work_flag", False)
    return flags


# ============================================================================
# Dimension 1: Role & Title Fit (30%)
# ============================================================================
def score_role_fit(candidate):
    """
    How well does this candidate's title, seniority, and career profile
    match what the JD actually needs: a Senior AI/ML Engineer who ships
    production systems.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    years = profile.get("years_of_experience", 0)

    score = 0
    details = []

    # --- Title alignment (0-35 points) ---
    title_combined = f"{title} {headline}"

    # Strong fit titles get full credit
    if any(kw in title_combined for kw in STRONG_FIT_TITLE_KEYWORDS):
        title_score = 35
        details.append("title_strong_match")
    # Non-technical titles get very low credit
    elif any(nt in title for nt in NON_TECHNICAL_TITLES):
        title_score = 5
        details.append("title_non_technical")
    else:
        title_score = 15
        details.append("title_neutral")

    score += title_score

    # --- Seniority fit (0-20 points) ---
    # JD says 5-9 years sweet spot, "ideal" is 6-8 years
    # JD note: "founding team wants growers" — heavily overqualified is a culture risk
    if 6 <= years <= 8:
        seniority_score = 20  # JD ideal band
    elif 5 <= years < 6 or 8 < years <= 9:
        seniority_score = 18  # JD stated range
    elif 9 < years <= 12:
        seniority_score = 14  # Slightly over, still viable
    elif 4 <= years < 5:
        seniority_score = 12  # JD says "4 years with strong signals is fine"
    elif 12 < years <= 15:
        seniority_score = 7   # Overqualified — founding team culture risk
    elif years > 15:
        seniority_score = 3   # Significantly overqualified (Series A != big-co comfort)
    elif 3 <= years < 4:
        seniority_score = 6
    else:
        seniority_score = max(0, int(years * 2))

    # Bonus for senior/lead in title
    if any(kw in title_combined for kw in ["senior", "sr.", "lead", "staff", "principal"]):
        seniority_score = min(20, seniority_score + 5)

    # Penalty for junior/intern titles
    if any(kw in title_combined for kw in WEAK_FIT_TITLE_KEYWORDS):
        seniority_score = max(0, seniority_score - 10)

    score += seniority_score

    # --- Production experience detection (0-25 points) ---
    career_text = _career_text(candidate)

    prod_count = sum(1 for ind in PRODUCTION_INDICATORS if ind in career_text)
    ml_prod_count = sum(1 for ind in ML_PRODUCTION_INDICATORS if ind in career_text)
    leadership_count = sum(1 for ind in LEADERSHIP_INDICATORS if ind in career_text)

    prod_score = min(15, prod_count * 3)
    ml_prod_score = min(10, ml_prod_count * 3)
    score += prod_score + ml_prod_score

    # --- Leadership bonus (0-10 points) ---
    if leadership_count >= 2:
        score += 10
    elif leadership_count >= 1:
        score += 5

    # --- Career trajectory consistency (0-10 points) ---
    # Check if career shows actual progression in ML/AI/Engineering
    career_titles = [j.get("title", "").lower() for j in career]
    tech_titles = sum(
        1 for t in career_titles
        if any(kw in t for kw in STRONG_FIT_TITLE_KEYWORDS)
    )
    if tech_titles >= 2:
        score += 10
    elif tech_titles >= 1:
        score += 5

    # --- Hidden gem: recommendation/ranking/search builder (0-8 points) ---
    # JD: "A Tier 5 candidate may not use 'RAG' or 'Pinecone' but if they
    #      built a recommendation system at a product company, they're a fit"
    hidden_gem_indicators = [
        "recommendation system", "recommender", "search system",
        "ranking system", "ranking model", "learning to rank",
        "retrieval system", "candidate matching", "relevance",
        "personalization", "collaborative filtering", "content-based",
        "hybrid search", "semantic search", "query understanding",
        "search relevance", "search quality", "recall", "precision",
        "matching engine", "information retrieval", "nearest neighbor",
        "vector search", "recommendations", "recommender system",
    ]
    gem_count = sum(1 for gi in hidden_gem_indicators if gi in career_text)
    if gem_count >= 3:
        score += 8
        details.append("hidden_gem_builder")
    elif gem_count >= 1:
        score += 4

    return clamp(score), details


# ============================================================================
# Dimension 2: Skills Depth & Relevance (25%)
# ============================================================================
def score_skills_depth(candidate):
    """
    Measures how deeply the candidate's skills match the specific
    JD requirements: embeddings, retrieval, vector DBs, Python, ranking.
    """
    sm = match_candidate_skills(
        candidate, JD_REQUIRED_SKILLS, JD_PREFERRED_SKILLS
    )

    # Base skill match score (0-40 points from ratio)
    match_score = sm["total_ratio"] * 40

    # Required skill coverage (0-20 points)
    req_score = sm["required_ratio"] * 20

    # Proficiency depth for matched skills (0-15 points)
    all_target = JD_REQUIRED_SKILLS + JD_PREFERRED_SKILLS
    prof_score = get_skill_proficiency_score(candidate, all_target) * 0.15

    evidence = _applied_ml_system_evidence(candidate)
    technical_depth = _technical_career_depth(candidate)

    # Core AI skill count bonus (0-15 points). This is intentionally reduced
    # when a large explicit AI skill list has no supporting career evidence.
    core_count = count_core_ai_skills(candidate)
    core_score = min(15, core_count * 2)
    if core_count >= 5 and technical_depth <= 1:
        core_score *= 0.35

    # Endorsement credibility (0-5 points)
    endorse_score = get_skill_endorsement_score(candidate, all_target) * 0.05

    # Assessment verification bonus (0-5 points)
    sig = candidate.get("redrob_signals", {})
    assessments = sig.get("skill_assessment_scores", {})
    relevant_assessments = [
        v for k, v in assessments.items()
        if normalize_skill(k) in CORE_AI_SKILLS
    ]
    if relevant_assessments:
        avg_assessment = sum(relevant_assessments) / len(relevant_assessments)
        assess_bonus = min(5, avg_assessment * 0.05)
    else:
        assess_bonus = 0

    # Career evidence bonus (0-12 points): a candidate who built search,
    # ranking, retrieval, or recommendation systems can be strong even without
    # listing every trendy vector/LLM tool in their skills section.
    career_evidence_bonus = evidence["score"]
    if evidence["score"] >= 8 and sm["required_ratio"] < 0.35:
        career_evidence_bonus += 3

    total = (
        match_score + req_score + prof_score + core_score + endorse_score
        + assess_bonus + career_evidence_bonus
    )

    return clamp(total), sm


# ============================================================================
# Dimension 3: Career Quality & Trajectory (20%)
# ============================================================================
def score_career_quality(candidate):
    """
    Evaluates career trajectory, company quality, and the specific
    disqualifiers mentioned in the JD.
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    years = profile.get("years_of_experience", 0)

    if not career:
        return 20, {"issue": "no_career_history"}

    score = 0
    flags = {}

    # --- Consulting firm penalty (critical from JD) ---
    all_companies = [j.get("company", "").lower().strip() for j in career]
    current_company = profile.get("current_company", "").lower().strip()

    # Remove fictional companies from the check
    real_companies = [c for c in all_companies if c not in FICTIONAL_COMPANIES]

    consulting_count = sum(
        1 for c in real_companies
        if any(cf in c for cf in CONSULTING_FIRMS)
    )

    if consulting_count > 0 and consulting_count == len(real_companies):
        # Entire career at consulting firms — heavy penalty
        score -= 30
        flags["entire_career_consulting"] = True
    elif consulting_count > 0:
        # Currently at consulting but has product experience
        if any(cf in current_company for cf in CONSULTING_FIRMS):
            score -= 5  # Mild penalty, has prior product experience
            flags["current_consulting_prior_product"] = True

    # --- Career progression (0-25 points) ---
    def title_level(t):
        t_lower = t.lower()
        best = 4  # default engineer level
        for keyword, level in SENIORITY_LEVELS.items():
            if keyword in t_lower:
                best = max(best, level)
        return best

    promotions = 0
    for i in range(1, len(career)):
        older_level = title_level(career[i].get("title", ""))
        newer_level = title_level(career[i - 1].get("title", ""))
        if newer_level > older_level:
            promotions += 1

    promo_rate = min(1, promotions / max(years / 3, 1))
    score += promo_rate * 15

    # Career arc (first title → current title)
    if len(career) >= 2:
        first_level = title_level(career[-1].get("title", ""))
        current_level = title_level(career[0].get("title", ""))
        if current_level > first_level:
            score += 10
        elif current_level == first_level:
            score += 5

    # --- Tenure stability (0-20 points) ---
    tenures = [j.get("duration_months", 0) for j in career]
    avg_tenure = sum(tenures) / len(tenures) if tenures else 0

    # JD explicitly warns against title-chasers switching every 1.5 years
    short_stints = sum(1 for t in tenures if t < 18)

    if avg_tenure >= 30:
        score += 20
    elif avg_tenure >= 24:
        score += 15
    elif avg_tenure >= 18:
        score += 10
    elif avg_tenure >= 12:
        score += 5
    else:
        score += 0

    if short_stints >= 3:
        score -= 10
        flags["title_chaser_risk"] = True
    elif short_stints >= 2:
        score -= 5

    # --- Product company experience (0-20 points) ---
    product_indicators = [
        "product", "saas", "fintech", "e-commerce", "marketplace",
        "platform", "consumer", "startup", "technology",
    ]
    career_industries = [j.get("industry", "").lower() for j in career]
    career_descriptions = " ".join(j.get("description", "").lower() for j in career)

    product_exp = sum(
        1 for ind in career_industries
        if any(pi in ind for pi in product_indicators)
    )
    product_desc = sum(
        1 for pi in product_indicators
        if pi in career_descriptions
    )

    if product_exp >= 2 or product_desc >= 3:
        score += 20
    elif product_exp >= 1 or product_desc >= 1:
        score += 10
    else:
        score += 5

    # --- Pre-LLM ML experience bonus (0-15 points, increased from 10) ---
    # JD says: "people who understood retrieval and ranking before it became fashionable"
    pre_llm_depth = 0
    for job in career:
        start = job.get("start_date", "")
        desc = job.get("description", "").lower()
        if start and start < "2022-01-01":
            ml_terms = ["machine learning", "ml ", "model", "algorithm",
                        "recommendation", "ranking", "retrieval", "nlp",
                        "neural", "deep learning", "embedding",
                        "search", "information retrieval", "vector"]
            matches = sum(1 for t in ml_terms if t in desc)
            if matches >= 1:
                pre_llm_depth = max(pre_llm_depth, min(matches, 4))
                flags["pre_llm_ml_experience"] = True

    if pre_llm_depth >= 3:
        score += 15  # Deep pre-LLM ML experience
    elif pre_llm_depth >= 2:
        score += 12
    elif pre_llm_depth >= 1:
        score += 8

    # --- Recent-only AI penalty ---
    # JD: "If your AI experience is primarily recent (<12mo) LangChain/OpenAI projects"
    # Detect candidates whose ALL ML career entries are post-2023
    if not flags.get("pre_llm_ml_experience"):
        all_career_starts = [j.get("start_date", "") for j in career]
        ml_career_starts = []
        for job in career:
            desc = job.get("description", "").lower()
            title_j = job.get("title", "").lower()
            if any(t in desc or t in title_j for t in
                   ["ml", "machine learning", "ai ", "data scien",
                    "deep learning", "nlp", "model"]):
                ml_career_starts.append(job.get("start_date", ""))
        if ml_career_starts and all(s >= "2023-01-01" for s in ml_career_starts if s):
            score -= 8
            flags["recent_only_ai"] = True

    # --- Recent code-writing check (0-5 points) ---
    # JD says: if you haven't written production code in 18 months...
    current_job = career[0] if career else {}
    current_desc = current_job.get("description", "").lower()
    code_indicators = ["code", "implement", "built", "develop",
                       "engineer", "programm", "python", "system"]
    if any(ci in current_desc for ci in code_indicators):
        score += 5

    return clamp(score + 30), flags  # +30 baseline so score isn't negative-dominated


# ============================================================================
# Dimension 4: Behavioral Signals (15%)
# ============================================================================
def score_behavioral(candidate, baseline_date=None):
    """
    Behavioral signals from the Redrob platform.
    The JD explicitly states: a perfect candidate who hasn't logged in
    for 6 months with 5% response rate is NOT actually available.
    """
    sig = candidate.get("redrob_signals", {})
    if not sig:
        return 25

    if baseline_date is None:
        baseline_date = datetime(2026, 6, 1)

    score = 0

    # --- Profile recency (0-15 points) ---
    last_active = sig.get("last_active_date", "")
    if last_active:
        try:
            active_date = datetime.strptime(last_active[:10], "%Y-%m-%d")
            days_since = max(0, (baseline_date - active_date).days)
            if days_since <= 7:
                score += 15
            elif days_since <= 30:
                score += 12
            elif days_since <= 90:
                score += 8
            elif days_since <= 180:
                score += 4
            else:
                score += 1  # Very stale
        except ValueError:
            score += 5

    # --- Open to work (0-10 points) ---
    if sig.get("open_to_work_flag", False):
        score += 10
    else:
        score += 2  # Passive candidates still valuable

    # --- Recruiter response rate (0-15 points) ---
    response_rate = sig.get("recruiter_response_rate", 0)
    score += min(15, response_rate * 15)

    # --- Profile completeness (0-8 points) ---
    completeness = sig.get("profile_completeness_score", 0)
    score += min(8, completeness * 0.08)

    # --- Verification trust score (0-12 points / -15 penalty) ---
    verified = 0
    if sig.get("verified_email", False):
        verified += 1
    if sig.get("verified_phone", False):
        verified += 1
    if sig.get("linkedin_connected", False):
        verified += 1

    if verified == 3:
        score += 12
    elif verified == 2:
        score += 8
    elif verified == 1:
        score += 4
    else:
        score -= 15  # High spam/bot probability

    # --- Market demand: saved by recruiters (0-10 points, log scaled) ---
    saves = sig.get("saved_by_recruiters_30d", 0)
    if saves > 0:
        score += min(10, math.log10(1 + saves) / 1.9 * 10)

    # --- Interview completion rate (0-8 points) ---
    interview_rate = sig.get("interview_completion_rate", 0.5)
    score += min(8, interview_rate * 8)

    # --- Offer acceptance reliability (bonus/penalty) ---
    offer_rate = sig.get("offer_acceptance_rate", -1)
    if offer_rate >= 0:
        if offer_rate > 0.8:
            score += 8  # Reliable closer
        elif offer_rate < 0.4:
            score -= 10  # Flaky, wastes recruiter time

    # --- Notice period (JD prefers sub-30 day) ---
    notice = sig.get("notice_period_days", 60)
    if notice <= 30:
        score += 8
    elif notice <= 60:
        score += 4
    elif notice <= 90:
        score += 0
    else:
        score -= 5  # Long notice period

    # --- GitHub activity (bonus for engineering roles) ---
    github = sig.get("github_activity_score", -1)
    if github >= 50:
        score += 8
    elif github >= 20:
        score += 4
    elif github > 0:
        score += 2

    # --- Response time (bonus for fast responders) ---
    resp_time = sig.get("avg_response_time_hours", 200)
    if resp_time <= 24:
        score += 5
    elif resp_time <= 72:
        score += 2

    return clamp(score)


# ============================================================================
# Dimension 5: Cultural Alignment (10%)
# ============================================================================
def score_cultural(candidate):
    """
    Location, company stage fit, domain alignment.
    JD: Pune/Noida preferred, hybrid, Series A startup.
    """
    profile = candidate.get("profile", {})
    sig = candidate.get("redrob_signals", {})

    score = 0

    # --- Location fit (0-30 points) ---
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    relocate = sig.get("willing_to_relocate", False)

    if any(loc in location for loc in ["pune", "noida"]):
        score += 30
    elif any(loc in location for loc in PREFERRED_LOCATIONS):
        score += 20
    elif country == "india" or any(loc in location for loc in INDIA_LOCATIONS):
        if relocate:
            score += 15
        else:
            score += 10
    elif relocate:
        score += 5
    else:
        score += 0  # Outside India, not willing to relocate

    # --- Work mode alignment (0-15 points) ---
    work_mode = sig.get("preferred_work_mode", "")
    if work_mode in ("hybrid", "flexible"):
        score += 15
    elif work_mode == "onsite":
        score += 12
    elif work_mode == "remote":
        score += 8

    # --- Company stage fit (0-20 points) ---
    # JD is Series A startup, wants people comfortable with ambiguity
    company_size = profile.get("current_company_size", "")
    if company_size in ("1-10", "11-50", "51-200"):
        score += 20  # Startup experience
    elif company_size in ("201-500", "501-1000"):
        score += 15  # Mid-stage
    elif company_size in ("1001-5000"):
        score += 10
    else:
        score += 5  # Large enterprise (less startup-culture fit)

    # --- Domain alignment (0-20 points) ---
    industry = profile.get("current_industry", "").lower()
    ai_domains = ["ai", "artificial intelligence", "machine learning",
                  "data", "technology", "software", "saas", "platform"]
    hr_tech = ["hr", "human resource", "recruiting", "talent", "hiring"]

    if any(d in industry for d in hr_tech):
        score += 20  # Perfect domain match (HR-tech)
    elif any(d in industry for d in ai_domains):
        score += 15
    elif "it services" in industry:
        score += 5  # Generic IT services
    else:
        score += 3

    # --- Salary alignment (0-15 points) ---
    salary = sig.get("expected_salary_range_inr_lpa", {})
    if salary:
        max_salary = salary.get("max", 0)
        # Realistic range for Senior AI Engineer at a Series A in India
        # JD: Pune/Noida, 5-9yr, founding team — typical band 25-55 LPA
        if 25 <= max_salary <= 55:
            score += 15  # Perfect Series A range
        elif 15 <= max_salary < 25:
            score += 8   # Low but acceptable
        elif 55 < max_salary <= 80:
            score += 5   # Expensive but possible for Series A
        elif max_salary > 80:
            score += 2   # Likely too expensive
        elif max_salary < 15:
            score += 2   # Suspiciously low — possibly wrong/missing data

    return clamp(score)


# ============================================================================
# Composite scorer
# ============================================================================
def compute_composite_score(candidate, tfidf_similarity=0.0, config=None):
    """
    Compute the final composite score for a candidate.

    Returns a dict with:
        - composite: final score (0-100)
        - dimensions: individual dimension scores
        - is_honeypot: bool
        - is_keyword_stuffer: bool
        - flags: dict of notable flags
        - skill_match: skill matching details
    """
    if config is None:
        config = ScoringConfig()

    profile = candidate.get("profile", {})
    years = profile.get("years_of_experience", 0)

    logger.debug(f"Computing composite score for candidate")

    # Check for honeypot
    is_honeypot, honeypot_reasons = detect_honeypot(candidate)
    is_stuffer, stuffer_confidence = detect_keyword_stuffer(candidate)

    if is_honeypot:
        return {
            "composite": 0,
            "dimensions": {},
            "is_honeypot": True,
            "honeypot_reasons": honeypot_reasons,
            "is_keyword_stuffer": is_stuffer,
            "flags": {"eliminated": "honeypot"},
            "skill_match": None,
        }

    # Score each dimension
    role_score, role_details = score_role_fit(candidate)
    skills_score, skill_match = score_skills_depth(candidate)
    career_score, career_flags = score_career_quality(candidate)
    behavioral_score = score_behavioral(candidate, config.baseline_date)
    cultural_score = score_cultural(candidate)
    availability_flags = _availability_flags(candidate, config.baseline_date)
    career_evidence = _applied_ml_system_evidence(candidate)
    technical_depth = _technical_career_depth(candidate)

    # TF-IDF similarity as a separate multiplier (not additive to skills)
    # Scale: 0.0-0.3 typical range → 0.85-1.15 multiplier
    tfidf_multiplier = 0.85 + min(0.30, tfidf_similarity / 0.25 * 0.30)

    dimensions = {
        "role_fit": role_score,
        "skills_depth": skills_score,
        "career_quality": career_score,
        "behavioral": behavioral_score,
        "cultural": cultural_score,
    }

    # Weighted composite
    composite = sum(
        dimensions[dim] * weight
        for dim, weight in SCORING_WEIGHTS.items()
    )

    # Apply TF-IDF as a global multiplier on the composite
    composite *= tfidf_multiplier

    # Apply keyword stuffer penalty
    if is_stuffer:
        penalty = stuffer_confidence * 40
        composite = max(0, composite - penalty)

    # Apply role/career mismatch penalty. This catches candidates whose skills
    # list is AI-heavy but whose title and career remain non-technical.
    if _is_non_technical_profile(candidate) and technical_depth <= 1:
        composite *= 0.55
        career_flags["role_career_mismatch"] = True

    # GAP 4 — CV/Speech/Robotics specialist without NLP/IR exposure
    # JD: "We respect your work but you'd be re-learning fundamentals here."
    if _is_cv_speech_specialist(candidate):
        composite *= 0.72
        career_flags["cv_speech_specialist_no_nlp"] = True

    # GAP 5 — Pure academic/research role without production deployment
    # JD: "We will not move forward. We've tried it twice."
    if _is_pure_researcher(candidate):
        composite *= 0.60
        career_flags["pure_research_no_production"] = True

    # GAP 8 — No recent coding evidence in last 18 months
    # JD: "Senior engineer who hasn't written production code in 18 months
    #      because they moved into architecture roles — probably not."
    if not _has_recent_coding_evidence(candidate, config.baseline_date):
        composite *= 0.78
        career_flags["no_recent_coding_evidence"] = True

    # Apply consulting firm entire-career penalty
    if career_flags.get("entire_career_consulting"):
        composite *= 0.4  # 60% reduction

    # Apply recent-only-AI penalty
    if career_flags.get("recent_only_ai"):
        composite *= 0.85  # 15% reduction for bandwagon AI candidates

    # Apply availability penalty as a multiplier, not just a 15%-weighted
    # dimension, because stale/non-responsive profiles are low hiring value.
    if availability_flags.get("stale_profile") and availability_flags.get("very_low_response"):
        composite *= 0.72
        career_flags["availability_risk"] = "stale_and_very_low_response"
    elif availability_flags.get("stale_profile") or availability_flags.get("very_low_response"):
        composite *= 0.88
        career_flags["availability_risk"] = "stale_or_very_low_response"
    elif availability_flags.get("inactive_90d") and availability_flags.get("low_response"):
        composite *= 0.92
        career_flags["availability_risk"] = "inactive_and_low_response"

    # Boost genuine hidden gems after penalties: product/system evidence should
    # matter even when the skill list lacks explicit RAG/vector DB keywords.
    if career_evidence["score"] >= 8 and not career_flags.get("role_career_mismatch"):
        composite *= 1.08
        career_flags["hidden_gem_builder"] = True

    # The JD is senior/founding-team oriented. Strong adjacent builders with
    # less experience can still rank, but they should not outrank comparable
    # 5-9 year senior profiles purely because every other signal is excellent.
    if years < 4:
        composite *= 0.82
        career_flags["below_senior_experience_band"] = True
    elif years < 5:
        composite *= 0.93
        career_flags["slightly_below_senior_experience_band"] = True

    # Calibration: preserve score separation at the top instead of saturating
    # many candidates at exactly 100.
    composite = max(0, composite * 1.01)

    # Collect all flags
    flags = {}
    if career_flags:
        flags.update(career_flags)
    if is_stuffer:
        flags["keyword_stuffer"] = stuffer_confidence
    if role_details:
        flags["role_details"] = role_details
        if "hidden_gem_builder" in role_details:
            flags["hidden_gem_builder"] = True
    if career_evidence["families"]:
        flags["applied_ml_system_evidence"] = career_evidence["families"]

    return {
        "composite": composite,
        "dimensions": dimensions,
        "is_honeypot": False,
        "is_keyword_stuffer": is_stuffer,
        "flags": flags,
        "skill_match": skill_match,
    }
