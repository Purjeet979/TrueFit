# TrueFit — Methodology Document

## 1. Executive Summary

TrueFit is an intelligent candidate ranking system built for the Redrob AI Hackathon that goes far beyond keyword matching. It processes 100,000 candidates against the Senior AI Engineer JD using a **7-stage pipeline** with **5-dimensional multi-signal scoring**, **honeypot detection**, **keyword-stuffer detection**, and **explainable per-candidate reasoning**.

**Key Design Principle:** The JD explicitly states that the right answer involves "reasoning about the gap between what the JD says and what the JD means." Our system understands that a Marketing Manager with perfect AI keywords is a trap, while a Backend Engineer who built recommendation systems at a product company is a strong fit — even if their skill list doesn't include "RAG" or "Pinecone."

**Runtime:** 31.6 seconds in the latest full 100K local run on CPU. Optimized via `scikit-learn` and `numpy` for fast TF-IDF computation, zero API calls.

---

## 2. Architecture

```
candidates.jsonl (100K)
    │
    ├── Stage 1: Load & Parse
    ├── Stage 2: Hard Pre-Filters (eliminate obvious non-fits)
    │     └── Removes: <2yr exp, zero skills, no technical relevance
    ├── Stage 3: Honeypot Detection
    │     └── Removes: impossible profiles, expert-with-zero-duration, etc.
    ├── Stage 4: TF-IDF Semantic Similarity
    │     └── JD-vocabulary-only vectorization for speed
    ├── Stage 5: Multi-Signal Composite Scoring
    │     ├── Dimension 1: Role & Title Fit (30%)
    │     ├── Dimension 2: Skills Depth & Relevance (25%)
    │     ├── Dimension 3: Career Quality & Trajectory (20%)
    │     ├── Dimension 4: Behavioral Signals (15%)
    │     └── Dimension 5: Cultural Alignment (10%)
    ├── Stage 6: Ranking + Reasoning Generation
    └── Stage 7: CSV Output (Top 100)
```

---

## 3. Key Technical Decisions

### 3.1 Why Title-Career Coherence Matters More Than Skill Keywords

The dataset contains deliberate traps: candidates with titles like "Marketing Manager" or "HR Manager" who have extensive AI/ML skill lists (PyTorch, TensorFlow, NLP, etc.). A naive keyword matcher would rank these highly.

Our system detects this by:
1. **Title classification** — We categorize titles into "strong fit" (ML Engineer, Data Scientist, Software Engineer), "neutral," and "non-technical" (Marketing Manager, Accountant)
2. **Career description analysis** — We scan career history descriptions for actual technical indicators (not just skills listed)
3. **Coherence check** — A Marketing Manager with 5 AI skills but career descriptions about "SEO strategy" and "editorial calendar" is flagged as a keyword stuffer

### 3.2 Consulting Firm Penalty

The JD explicitly states: *"People who have only worked at consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, etc.) in their entire career"* are not a fit.

We implement this as:
- **Entire career at consulting firms:** 60% score reduction (0.4x multiplier)
- **Currently at consulting but has prior product experience:** Mild 5-point penalty (acceptable per JD)
- **Never at consulting:** No penalty

We maintain a list of 20+ consulting/services firms and handle fictional company names (Dunder Mifflin, Globex Inc, Stark Industries) separately.

### 3.3 Honeypot Detection

The dataset contains ~80 honeypot candidates with subtly impossible profiles. Our detector checks 8 independent signals:

1. **Expert proficiency with near-zero duration** — 3+ "expert" skills with ≤3 months usage
2. **High skill count with zero endorsements** — 12+ skills but 70%+ have 0 endorsements
3. **Title-skill extreme mismatch** — Non-technical title with 5+ AI/ML skills
4. **Career description disconnection** — AI-heavy skills but career descriptions lack any technical content
5. **Impossible tenure** — 8+ years at a tiny company (1-10 employees)
6. **Experience inflation** — Claims 10yr experience but career history totals 4yr
7. **Mass expert with zero assessments** — 6+ expert skills but zero platform assessments taken
8. **High completeness with zero verification** — 80%+ profile completeness but no email, phone, or LinkedIn verification and <10 connections

A candidate is flagged as a honeypot when they trigger 2+ independent signals.

### 3.4 TF-IDF Optimization for 100K Scale

Standard pure-Python TF-IDF across 100K documents is too slow. We optimize by:
- **Scikit-Learn & NumPy:** We use highly optimized C-backend operations (`TfidfVectorizer` and `cosine_similarity`) to rapidly compute semantic similarities.
- **JD-vocabulary-only:** We only track terms that appear in the JD, dramatically reducing the vocabulary size and memory footprint.
- **Pre-filter first:** Reducing the candidate pool from 100K to ~92K before TF-IDF.
- **Top-K cutoff:** We only process the top similarities for the expensive multi-signal scorer.

This achieves TF-IDF computation in ~20 seconds on CPU.

### 3.5 Pre-LLM Experience Detection

The JD explicitly says: *"people who understood retrieval and ranking before it became fashionable."* We detect pre-LLM ML experience by checking career history entries with start dates before 2022-01-01 for ML-related keywords (model, algorithm, recommendation, ranking, retrieval, neural).

---

## 4. Scoring Dimensions

### Dimension 1: Role & Title Fit (30% weight)

| Signal | Points | Rationale |
|---|---|---|
| Title contains ML/AI/Software Engineer keywords | 35 | Direct role alignment |
| Non-technical title (Marketing, HR, etc.) | 5 | Likely wrong domain |
| Experience 5-12 years | 20 | JD sweet spot |
| Senior/Lead/Staff in title | +5 | Seniority match |
| Production indicators in career | 0-15 | "Shipped to real users" |
| ML production indicators | 0-10 | Specific ML deployment experience |
| Leadership evidence | 0-10 | "Lead a team" per JD |
| Tech title consistency across career | 0-10 | Career coherence |

### Dimension 2: Skills Depth & Relevance (25% weight)

Multi-layer skill matching:
1. **Direct match** — Candidate skill list matches JD skill (with alias resolution)
2. **Career evidence** — Skill mentioned in career descriptions (75% credit)
3. **Profile evidence** — Skill mentioned in summary/headline (50% credit)

Required skills weighted 2x vs preferred skills. Proficiency levels, endorsement counts, and platform assessment scores provide additional validation.

### Dimension 3: Career Quality & Trajectory (20% weight)

| Signal | Weight | Notes |
|---|---|---|
| Consulting firm penalty | -30 to 0 | Entire career = heavy penalty |
| Career progression | 0-15 | Promotions per year |
| Career arc direction | 0-10 | First title → current title level |
| Tenure stability | 0-20 | Avg tenure, job-hopping detection |
| Product company experience | 0-20 | Industry and description analysis |
| Pre-LLM ML experience | 0-10 | Bonus for pre-2022 ML work |
| Recent code-writing | 0-5 | Still hands-on (per JD) |

### Dimension 4: Behavioral Signals (15% weight)

| Signal | Points | Rationale |
|---|---|---|
| Profile recency | 0-15 | "Hasn't logged in for 6 months = not available" |
| Open to work | 0-10 | Active job seeker |
| Recruiter response rate | 0-15 | Actually responds to outreach |
| Verification trust score | -15 to +12 | Spam/bot detection |
| Saved by recruiters | 0-10 | Market demand (log-scaled) |
| Interview completion | 0-8 | Follows through |
| Offer acceptance reliability | -10 to +8 | Doesn't waste cycles |
| Notice period | -5 to +8 | Sub-30 day preferred |
| GitHub activity | 0-8 | Technical validation |
| Response time | 0-5 | Fast responder bonus |

### Dimension 5: Cultural Alignment (10% weight)

| Signal | Points |
|---|---|
| Location: Pune/Noida | 30 |
| Location: Other preferred Indian cities | 20 |
| Location: India + willing to relocate | 15 |
| Work mode: hybrid/flexible | 15 |
| Company size: startup (1-200) | 20 |
| Domain: HR-tech | 20, AI/tech: 15 |
| Salary: 15-60 LPA range | 15 |

---

## 5. Reasoning Generation

Each candidate receives a specific, factual 1-2 sentence reasoning that:
- References specific data from their profile (years, title, company, skills)
- Connects to JD requirements
- Acknowledges honest concerns for candidates with gaps
- Varies substantively between candidates (not templated)

Top-20 candidates get strength-focused reasoning with secondary behavioral signals.
Mid-tier (21-60) get balanced skill match + concern summaries.
Lower-tier (61-100) get honest explanations of why they rank lower.

---

## 6. What We Explicitly Avoid

1. **Keyword counting** — The dataset is designed to trap keyword matchers
2. **LLM API calls** — Zero network calls, all computation local
3. **GPU dependency** — Pure CPU, pure Python
4. **Hosted services** — Uses no hosted models or external APIs during ranking; dependencies are local CPU packages listed in `requirements.txt`
5. **Template reasoning** — Each reasoning is generated from candidate-specific data
6. **Ignoring behavioral signals** — A perfect-on-paper candidate with 5% response rate is down-weighted

---

## 7. Reproducibility

```bash
# Single command to reproduce
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# Validate output
python validate_submission.py submission.csv
```

Runtime: 31.6 seconds in the latest full 100K local run (well within 5-minute constraint)
Memory: comfortably within the 16 GB constraint
Dependencies: `numpy`, `scikit-learn` (see `requirements.txt`)

---

## 8. AI Tools Declaration

AI tools (Claude, Gemini) were used for:
- Architecture discussion and code review
- Debugging and refactoring
- No candidate data was processed through any LLM
- All ranking logic is deterministic and rule-based

---

*Built by Purjeet for the India Runs Data and AI Challenge.*
