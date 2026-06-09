import streamlit as st
import pandas as pd
import time
import json
from pathlib import Path
import sys

# Add the current directory to sys.path so we can import ranker
sys.path.append(str(Path(__file__).parent))

from ranker.loader import extract_candidate_text
from ranker.constants import JD_TEXT
from ranker.tfidf import TFIDFCache
from ranker.honeypot import detect_honeypot
from ranker.reasoning import generate_reasoning
from ranker.utils import setup_logger, ScoringConfig, safe_score_candidate, get_candidate_id

logger = setup_logger(__name__)

st.set_page_config(
    page_title="TrueFit Ranker Sandbox",
    page_icon="🎯",
    layout="wide"
)

st.title("🎯 TrueFit Intelligent Ranker - Sandbox Demo")
st.markdown("""
This is a live demo of the TrueFit candidate ranking system built for the Redrob AI Challenge.
It runs the exact same **7-stage pipeline** used to generate our `submission.csv`, including:
- Honeypot & Keyword Stuffer Detection
- TF-IDF Semantic Matching
- 5-Dimensional Composite Scoring (Role Fit, Skills Depth, Career Quality, Behavioral, Cultural)
- Rule-based Reasoning Generation
""")

# Load a sample of candidates (or upload)
uploaded_file = st.file_uploader("Upload candidates (JSONL format) to rank", type=["jsonl"])

# Instantiate the cache outside so it persists across re-runs if Streamlit cache allows,
# or we can just use Streamlit's cache_resource for the TFIDF cache.
@st.cache_resource
def get_tfidf_cache():
    return TFIDFCache()

@st.cache_data
def process_candidates(candidates_data):
    start_time = time.time()
    
    # 1. Load
    candidates = []
    for line in candidates_data.splitlines():
        if line.strip():
            try:
                candidates.append(json.loads(line))
            except Exception as e:
                logger.warning(f"Failed to parse line in Streamlit: {e}")
            
    # 2. Pre-filter & Extract
    valid_cands = []
    cand_texts = []
    for i, c in enumerate(candidates):
        profile = c.get("profile", {})
        title = profile.get("current_title", "").lower()
        if any(kw in title for kw in ["marketing", "sales", "hr", "accountant", "customer support"]):
            continue
        if profile.get("years_of_experience", 0) < 3:
            continue
            
        valid_cands.append(c)
        cand_texts.append((len(valid_cands)-1, extract_candidate_text(c)))
        
    # 3. Honeypot Detection
    clean_cands = []
    clean_texts = []
    honeypots_caught = 0
    for i, c in enumerate(valid_cands):
        is_hp, _ = detect_honeypot(c)
        if not is_hp:
            clean_cands.append(c)
            clean_texts.append((len(clean_cands)-1, cand_texts[i][1]))
        else:
            honeypots_caught += 1
            
    # 4. TF-IDF
    tfidf_scores = {}
    if clean_texts:
        tfidf_cache = get_tfidf_cache()
        sim_results = tfidf_cache.compute_with_caching(JD_TEXT, clean_texts, top_k=min(100, len(clean_texts)))
        for cand_idx, score in sim_results:
            tfidf_scores[cand_idx] = score
            
    # 5 & 6. Scoring & Reasoning
    results = []
    config = ScoringConfig()
    
    for i, c in enumerate(clean_cands):
        if i not in tfidf_scores and len(clean_texts) > 100:
            continue # Skip scoring if not in top K TF-IDF and dataset is large
            
        tfidf = tfidf_scores.get(i, 0.0)
        result_dict = safe_score_candidate(c, tfidf, config)
        
        if result_dict:
            results.append({
                "candidate": c,
                "score": result_dict.get("composite", 0) / 100,
                "result_dict": result_dict
            })
        
    # 7. Rank
    results.sort(key=lambda x: x["score"], reverse=True)
    
    final_output = []
    for rank, res in enumerate(results[:100], 1):
        cand = res["candidate"]
        reasoning = generate_reasoning(cand, res["result_dict"], rank)
        
        candidate_id = get_candidate_id(cand)
        
        final_output.append({
            "Rank": rank,
            "Candidate ID": candidate_id,
            "Name": cand.get("profile", {}).get("name"),
            "Title": cand.get("profile", {}).get("current_title"),
            "Experience (Yrs)": cand.get("profile", {}).get("years_of_experience"),
            "Score": f"{res['score']:.4f}",
            "Reasoning": reasoning
        })
        
    end_time = time.time()
    
    return {
        "results": final_output,
        "runtime": end_time - start_time,
        "total_loaded": len(candidates),
        "honeypots": honeypots_caught,
        "final_count": len(results)
    }

if uploaded_file is not None:
    content = uploaded_file.getvalue().decode("utf-8")
    with st.spinner('Running Ranking Pipeline...'):
        out = process_candidates(content)
        
    st.success(f"Pipeline completed in {out['runtime']:.2f} seconds!")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Candidates Loaded", out["total_loaded"])
    col2.metric("Honeypots Blocked", out["honeypots"])
    col3.metric("Ranked Output", out["final_count"])
    
    st.subheader("🏆 Top Ranked Candidates")
    st.dataframe(pd.DataFrame(out["results"]), use_container_width=True)
else:
    st.info("Please upload a subset of `candidates.jsonl` (e.g. 500 lines) to see the pipeline in action. (Due to Streamlit memory limits, do not upload the full 500MB file).")

st.markdown("---")
st.markdown("**Built for Redrob AI Challenge** | Engine: Pure Python + Scikit-Learn | Deterministic Rule-based Scoring")
