# 🚀 TrueFit — Intelligent Candidate Discovery & Ranking

TrueFit is an advanced AI-powered candidate ranking system built for the **India Runs Data and AI Challenge**. It processes **100,000 candidates** against a specific Job Description using a **7-stage multi-signal pipeline** that goes far beyond keyword matching — understanding title-career coherence, detecting dataset traps and honeypots, weighing behavioral signals, and producing explainable per-candidate reasoning.

## 🏆 Key Innovations

### Beyond Keyword Matching
The JD explicitly warns: *"The right answer is not 'find candidates whose skills section contains the most AI keywords.'"* Our system:
- Detects **keyword stuffers** (e.g., Marketing Managers with perfect AI skill lists)
- Catches **~80 honeypots** with impossible profiles (expert skills with zero duration)
- Penalizes **entire-career-at-consulting** candidates per JD requirements
- Rewards **production ML experience** detected in career descriptions, not just skill tags
- Understands **pre-LLM ML experience** (pre-2022 work matters more)

### Architecture Overview
```
candidates.jsonl (100K)
    ├── Stage 1: Load & Parse
    ├── Stage 2: Hard Pre-Filters (experience, technical relevance)
    ├── Stage 3: Honeypot Detection (10 independent signals)
    ├── Stage 4: TF-IDF Semantic Similarity (JD-vocabulary-only)
    ├── Stage 5: 5-Dimensional Multi-Signal Scoring
    │     ├── Role & Title Fit (30%)
    │     ├── Skills Depth & Relevance (25%)
    │     ├── Career Quality & Trajectory (20%)
    │     ├── Behavioral Signals (15%)
    │     └── Cultural Alignment (10%)
    ├── Stage 6: Ranking + Per-Candidate Reasoning
    └── Stage 7: CSV Output (Top 100)
```

## ⚡ Quick Start — Reproduce the Submission

As per Section 10.3 of the submission spec, run this exact command to reproduce the CSV:

```bash
# Single command to produce the ranked submission CSV
python rank.py --candidates ./candidates.jsonl --out ./HaXker.csv

# Final local validation before upload
python validate_submission.py ./HaXker.csv --candidates ./candidates.jsonl
```

**Constraints met:**
- ✅ Runtime: ~250 seconds (limit: 300s)
- ✅ Memory: ~800 MB peak (limit: 16 GB)
- ✅ CPU only, no GPU
- ✅ Uses NumPy & Scikit-Learn for highly optimized TF-IDF
- ✅ No network/API calls
- ✅ Output validation checks exact header, 100 rows, ranks 1-100, unique IDs, and monotonic scores

## 🧠 Scoring Dimensions

| Dimension | Weight | What It Measures |
|---|---|---|
| **Role & Title Fit** | 30% | Title alignment, seniority, production experience in career descriptions |
| **Skills Depth** | 25% | JD-specific skill matching with alias resolution, proficiency, assessments |
| **Career Quality** | 20% | Product company experience, tenure stability, consulting firm penalty |
| **Behavioral Signals** | 15% | Activity recency, response rate, verification, notice period |
| **Cultural Alignment** | 10% | Location, work mode, company stage, salary alignment |

## 🛡️ Trap Detection

- **Honeypot Detection:** 10 independent signals including expert-with-zero-duration, impossible tenure, impossible progression, experience inflation, and verification-completeness mismatch. Blocked exactly 55 honeypots.
- **Keyword Stuffer Detection:** Non-technical title + AI-heavy skills + non-technical career descriptions.
- **Recent-only AI Penalty:** Penalizes candidates whose AI experience only started post-2023 without pre-LLM fundamentals.
- **Consulting Firm Penalty:** Entire career at consulting firms triggers a massive score reduction.
- **Title-Career Coherence:** Skills are validated against actual career descriptions, detecting hidden gems (people who built recommendation systems but lack buzzwords).



## 📁 Project Structure

```
```
├── rank.py                  # Main entry point for submission CSV generation
├── app.py                   # Streamlit Sandbox Demo application
├── ranker/                  # Python ranking engine
│   ├── constants.py         # Skill aliases, JD signals, weights
│   ├── loader.py            # JSONL parsing, text extraction
│   ├── honeypot.py          # Honeypot & keyword stuffer detection
│   ├── skill_matcher.py     # Multi-strategy skill matching with aliases
│   ├── tfidf.py             # Optimized Scikit-Learn TF-IDF + cosine similarity
│   ├── scorer.py            # 5-dimensional multi-signal scoring
│   └── reasoning.py         # Per-candidate reasoning generation
├── HaXker.csv               # Generated ranked output (top 100)
├── METHODOLOGY.md           # Detailed methodology document
├── submission_metadata.yaml # Submission metadata mapping to portal
└── requirements.txt         # Dependencies (scikit-learn, numpy, pandas, streamlit)
```

## 📄 Documentation

- **[METHODOLOGY.md](METHODOLOGY.md)** — Full technical methodology, scoring dimensions, and design rationale
- **[submission_metadata.yaml](submission_metadata.yaml)** — Submission metadata for the hackathon portal

---

## 👨‍💻 Developed By

Built with ❤️ by **Purjeet** for the *India Runs Data and AI Challenge*.

*Contact: parthshahu9506@gmail.com*
*GitHub: [Purjeet979](https://github.com/Purjeet979)*
