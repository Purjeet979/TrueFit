"""
Honeypot detection for the Redrob dataset.

The dataset contains ~80 honeypot candidates with subtly impossible profiles:
- 8 years experience at a company founded 3 years ago
- "Expert" proficiency in 10 skills with 0 duration_months each
- Skills that completely contradict career history
- Suspiciously perfect profiles with no verification

These are forced to relevance tier 0 in the ground truth.
If honeypot rate > 10% in top 100, submission is disqualified.
"""
from .utils import setup_logger

logger = setup_logger(__name__)

def detect_honeypot(candidate):
    """
    Returns (is_honeypot: bool, reasons: list[str]).
    Multiple signals are checked; a candidate is flagged if they trigger
    2 or more independent honeypot signals.
    """
    reasons = []
    signals = 0

    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])
    sig = candidate.get("redrob_signals", {})

    # ---- Signal 1: Expert proficiency with near-zero duration ----
    expert_skills = [s for s in skills if s.get("proficiency") == "expert"]
    zero_duration_experts = [
        s for s in expert_skills
        if s.get("duration_months", 0) <= 3
    ]
    if len(zero_duration_experts) >= 3:
        reasons.append(
            f"{len(zero_duration_experts)} 'expert' skills with <=3 months usage"
        )
        signals += 2  # Very strong signal

    # ---- Signal 2: Very high skill count with mostly low endorsements ----
    if len(skills) >= 12:
        zero_endorse = sum(1 for s in skills if s.get("endorsements", 0) == 0)
        if zero_endorse >= len(skills) * 0.7:
            reasons.append(
                f"{len(skills)} skills but {zero_endorse} have 0 endorsements"
            )
            signals += 1

    # ---- Signal 3: Title-skill extreme mismatch ----
    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    non_tech_titles = {
        "marketing manager", "hr manager", "operations manager",
        "accountant", "sales executive", "customer support",
        "content writer", "graphic designer", "mechanical engineer",
        "civil engineer",
    }
    has_non_tech_title = any(nt in title for nt in non_tech_titles)

    ai_skill_names = {
        "pytorch", "tensorflow", "keras", "nlp", "deep learning",
        "machine learning", "transformers", "bert", "gpt",
        "rag", "langchain", "llamaindex", "fine-tuning",
        "lora", "computer vision", "gans", "faiss",
        "sentence-transformers", "embeddings",
    }
    candidate_skill_names = {s.get("name", "").lower() for s in skills}
    ai_skill_count = len(candidate_skill_names & ai_skill_names)

    if has_non_tech_title and ai_skill_count >= 5:
        reasons.append(
            f"Non-technical title '{title}' with {ai_skill_count} AI/ML skills"
        )
        signals += 1

    # ---- Signal 4: Career history description mismatch ----
    # Check if career descriptions describe completely different work
    # than what the title/skills claim
    if career:
        career_text = " ".join(
            j.get("description", "") for j in career
        ).lower()

        tech_career_indicators = [
            "model", "training", "inference", "pipeline", "deploy",
            "algorithm", "neural", "embedding", "vector", "ml ",
            "machine learning", "deep learning", "nlp", "data science",
        ]
        tech_career_count = sum(
            1 for ind in tech_career_indicators if ind in career_text
        )

        # Non-tech career descriptions but AI-heavy skill list
        if ai_skill_count >= 4 and tech_career_count <= 1:
            reasons.append(
                "AI-heavy skills but career descriptions lack technical content"
            )
            signals += 1

    # ---- Signal 5: Impossibly long tenure at small/new company ----
    for job in career:
        duration = job.get("duration_months", 0)
        company_size = job.get("company_size", "")
        if company_size in ("1-10", "11-50") and duration > 96:
            reasons.append(
                f"Tenure of {duration} months at tiny company ({company_size})"
            )
            signals += 1
            break

    # ---- Signal 6: Experience years vs career history mismatch ----
    total_career_months = sum(
        j.get("duration_months", 0) for j in career
    )
    claimed_years = profile.get("years_of_experience", 0)
    if claimed_years > 0 and total_career_months > 0:
        career_years = total_career_months / 12
        # If claimed experience is massively more than career history shows
        if claimed_years > career_years * 2.5 and claimed_years > 5:
            reasons.append(
                f"Claims {claimed_years:.1f}yr experience but career history "
                f"totals only {career_years:.1f}yr"
            )
            signals += 1

    # ---- Signal 7: All skills at expert with zero assessments ----
    if len(expert_skills) >= 6:
        assessments = sig.get("skill_assessment_scores", {})
        if len(assessments) == 0:
            reasons.append(
                f"{len(expert_skills)} expert skills but zero assessments taken"
            )
            signals += 1

    # ---- Signal 8: Profile completeness vs verification mismatch ----
    completeness = sig.get("profile_completeness_score", 0)
    verified_email = sig.get("verified_email", False)
    verified_phone = sig.get("verified_phone", False)
    linkedin = sig.get("linkedin_connected", False)
    connections = sig.get("connection_count", 0)

    if completeness > 80 and not verified_email and not verified_phone \
            and not linkedin and connections < 10:
        reasons.append(
            "High profile completeness but zero verification and minimal connections"
        )
        signals += 1

    # ---- Signal 9: Near-zero duration for majority of skills ----
    if len(skills) >= 8:
        zero_dur = sum(1 for s in skills if s.get("duration_months", 0) == 0)
        if zero_dur >= len(skills) * 0.8:
            reasons.append(f"{zero_dur}/{len(skills)} skills have 0 months duration")
            signals += 1

    # ---- Signal 10: Impossible progression ----
    if len(career) >= 2:
        first_title = career[-1].get("title", "").lower()
        curr_title = career[0].get("title", "").lower()
        if any(kw in first_title for kw in ["intern", "trainee", "student"]) and \
           any(kw in curr_title for kw in ["principal", "vp", "director", "head"]) and \
           claimed_years < 4:
            reasons.append(f"Impossible progression: {first_title} to {curr_title} in {claimed_years}yrs")
            signals += 1

    # Threshold: 2+ signals = honeypot
    is_honeypot = signals >= 2
    return is_honeypot, reasons


def detect_keyword_stuffer(candidate):
    """
    Detect candidates who are keyword stuffers — high skill count in AI/ML
    but title and career history don't support it.
    Returns (is_stuffer: bool, confidence: float 0-1)
    """
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    career = candidate.get("career_history", [])

    title = profile.get("current_title", "").lower()
    headline = profile.get("headline", "").lower()
    summary = profile.get("summary", "").lower()

    # Count AI-relevant skills
    ai_keywords = {
        "python", "pytorch", "tensorflow", "keras", "nlp",
        "deep learning", "machine learning", "transformers", "bert",
        "gpt", "rag", "langchain", "llamaindex", "fine-tuning",
        "lora", "computer vision", "gans", "faiss", "milvus",
        "pinecone", "weaviate", "chromadb", "embeddings",
        "sentence-transformers", "scikit-learn", "spark", "airflow",
        "mlflow", "mlops", "docker", "kubernetes",
        "vector database", "vector db",
    }
    cand_skills = {s.get("name", "").lower() for s in skills}
    ai_match = len(cand_skills & ai_keywords)

    # Check if title is non-technical
    non_tech = any(nt in title for nt in [
        "marketing", "hr ", "human resource", "operations",
        "accountant", "accounting", "sales", "customer support",
        "content writer", "graphic design", "mechanical",
        "civil engineer",
    ])

    # Check career descriptions for actual technical content
    career_text = " ".join(j.get("description", "") for j in career).lower()
    tech_depth = sum(1 for kw in [
        "model", "training", "embedding", "vector", "pipeline",
        "algorithm", "neural", "inference", "deploy", "architecture",
        "ml ", "machine learning", "deep learning", "python",
    ] if kw in career_text)

    # Keyword stuffer: many AI skills + non-tech title + shallow career descriptions
    if non_tech and ai_match >= 4 and tech_depth <= 2:
        confidence = min(1.0, (ai_match - 3) * 0.15 + (0.3 if tech_depth == 0 else 0))
        return True, confidence

    # Also flag: summary is generic/templated AND has many AI skills
    generic_phrases = [
        "i've been curious about how ai tools could augment",
        "open to roles where i can apply my domain expertise",
        "experimented with chatgpt",
    ]
    is_generic_summary = sum(1 for p in generic_phrases if p in summary) >= 2

    if is_generic_summary and ai_match >= 3 and non_tech:
        return True, 0.7

    return False, 0.0
