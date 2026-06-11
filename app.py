import streamlit as st
import streamlit.components.v1 as components
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
    page_icon="💠",
    layout="wide"
)

premium_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600&family=Inter:wght@400;600&display=swap');

/* Animated Background (Deep Cyberpunk Dark) */
.stApp {
    background: linear-gradient(-45deg, #020617, #0f172a, #1e1b4b, #09090b, #000000);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
    font-family: 'Inter', sans-serif;
}
@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}



/* Glowing Typography */
h1 {
    font-family: 'Outfit', sans-serif !important;
    background: -webkit-linear-gradient(45deg, #fbcfe8, #f43f5e, #d946ef);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: glow 3s ease-in-out infinite alternate;
}
@keyframes glow {
    from { text-shadow: 0 0 10px rgba(244, 63, 94, 0.4); }
    to { text-shadow: 0 0 25px rgba(217, 70, 239, 0.8); }
}

/* Glassmorphism for Uploader and Metrics */
div[data-testid="stFileUploader"] > section, div[data-testid="metric-container"], div[data-testid="stAlert"] {
    background: rgba(255, 255, 255, 0.1) !important;
    backdrop-filter: blur(16px) !important;
    border-radius: 16px !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.4) !important;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
}

div[data-testid="stFileUploader"] > section:hover, div[data-testid="metric-container"]:hover {
    transform: translateY(-8px) scale(1.02) !important;
    box-shadow: 0 15px 45px 0 rgba(244, 63, 94, 0.4) !important;
    border: 1px solid rgba(244, 63, 94, 0.6) !important;
}

/* Specific text overrides for Uploader */
.stFileUploader small {
    color: #fbcfe8 !important;
}

/* Fix white headers and buttons */
header[data-testid="stHeader"] {
    background: transparent !important;
}
button[data-testid="stBaseButton-secondary"] {
    background-color: rgba(255, 255, 255, 0.05) !important;
    color: #fdf2f8 !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    backdrop-filter: blur(8px) !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
    background-color: rgba(255, 255, 255, 0.15) !important;
    border-color: #f43f5e !important;
    color: #f43f5e !important;
}

/* Metric text styling */
div[data-testid="metric-container"] {
    padding: 1.5rem !important;
    text-align: center;
}
div[data-testid="stMetricValue"] > div {
    color: #fda4af !important;
    font-size: 3rem !important;
    font-family: 'Outfit', sans-serif !important;
    font-weight: 600 !important;
    text-shadow: 0 0 10px rgba(253, 164, 175, 0.5);
}

/* Floating Ambient Particles (Pink/Red/Purple) */
.stApp::before {
    content: '';
    position: fixed;
    top: 0; left: 0; width: 100vw; height: 100vh;
    pointer-events: none;
    z-index: 0;
    background-image: 
        radial-gradient(circle at 20% 40%, rgba(244, 63, 94, 0.2) 0%, transparent 40%),
        radial-gradient(circle at 80% 20%, rgba(217, 70, 239, 0.2) 0%, transparent 40%),
        radial-gradient(circle at 60% 80%, rgba(225, 29, 72, 0.2) 0%, transparent 40%),
        radial-gradient(circle at 10% 90%, rgba(192, 38, 211, 0.2) 0%, transparent 40%);
    animation: float1 15s infinite ease-in-out alternate;
}
@keyframes float1 {
    0% { transform: translateY(0px) scale(1); }
    100% { transform: translateY(-40px) scale(1.2); }
}

/* Dataframe styling */
.stDataFrame {
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.15);
    box-shadow: 0 8px 32px 0 rgba(0,0,0,0.3);
}
.stMarkdown, div[data-testid="stVerticalBlock"], .stDataFrame {
    z-index: 1;
    position: relative;
}

</style>
"""

three_js_code = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { margin: 0; overflow: hidden; background: transparent; }
        canvas { display: block; width: 100vw; height: 100vh; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
</head>
<body>
    <script>
        // Break out of Streamlit's iframe restrictions to act as a full-screen background
        const iframe = window.frameElement;
        if (iframe) {
            iframe.style.position = 'fixed';
            iframe.style.top = '0';
            iframe.style.left = '0';
            iframe.style.width = '100vw';
            iframe.style.height = '100vh';
            iframe.style.zIndex = '0';
            iframe.style.border = 'none';
            iframe.style.pointerEvents = 'none'; // allow clicks to pass through to Streamlit UI
            
            let parentNode = iframe.parentElement;
            while(parentNode && parentNode.tagName !== 'BODY') {
                parentNode.style.position = 'static'; 
                parentNode.style.zIndex = '0';
                parentNode = parentNode.parentElement;
            }
        }

        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: false });
        renderer.setSize(window.innerWidth, window.innerHeight);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        document.body.appendChild(renderer.domElement);

        const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
        scene.add(ambientLight);
        const pointLight = new THREE.PointLight(0xf43f5e, 2);
        pointLight.position.set(5, 5, 5);
        scene.add(pointLight);
        const pointLight2 = new THREE.PointLight(0xd946ef, 2);
        pointLight2.position.set(-5, -5, 5);
        scene.add(pointLight2);

        const objects = [];
        const techStack = [
            "Purjeet", "Team HaXker", "Python", "Scikit-Learn", 
            "TF-IDF", "Streamlit", "Pandas", "NumPy", 
            "Regex", "Ranking Engine", "Deterministic AI", "JSONL"
        ];

        function createTextSprite(message) {
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.width = 512;
            canvas.height = 128;
            context.font = "Bold 50px 'Outfit', sans-serif";
            context.fillStyle = "rgba(244, 63, 94, 0.5)"; // glowing pink
            context.textAlign = "center";
            context.textBaseline = "middle";
            context.fillText(message, 256, 64);
            
            const texture = new THREE.CanvasTexture(canvas);
            const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
            const sprite = new THREE.Sprite(spriteMaterial);
            return sprite;
        }

        // Create a field of floating tech stack words
        for (let i = 0; i < 40; i++) {
            const word = techStack[i % techStack.length];
            const sprite = createTextSprite(word);
            
            sprite.position.set(
                (Math.random() - 0.5) * 40,
                (Math.random() - 0.5) * 30,
                (Math.random() - 0.5) * 15 - 10
            );
            const scale = Math.random() * 1 + 0.5;
            sprite.scale.set(5 * scale, 1.25 * scale, 1);
            
            sprite.userData = {
                floatSpeed: Math.random() * 0.01 + 0.005,
                floatOffset: Math.random() * Math.PI * 2,
                driftX: (Math.random() - 0.5) * 0.02
            };
            
            scene.add(sprite);
            objects.push(sprite);
        }

        camera.position.z = 5;

        // Mouse Parallax Logic
        let mouseX = 0;
        let mouseY = 0;
        let targetX = 0;
        let targetY = 0;
        const windowHalfX = window.innerWidth / 2;
        const windowHalfY = window.innerHeight / 2;

        try {
            window.parent.document.addEventListener('mousemove', (event) => {
                mouseX = (event.clientX - windowHalfX) * 0.002;
                mouseY = (event.clientY - windowHalfY) * 0.002;
            });
        } catch(e) { console.log("Cross-origin mouse tracking restricted"); }

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / window.innerHeight;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, window.innerHeight);
        });

        const clock = new THREE.Clock();
        function animate() {
            requestAnimationFrame(animate);
            const time = clock.getElapsedTime();

            targetX = mouseX * 2;
            targetY = mouseY * 2;

            // smooth camera movement
            camera.position.x += (targetX - camera.position.x) * 0.05;
            camera.position.y += (-targetY - camera.position.y) * 0.05;
            camera.lookAt(scene.position);

            objects.forEach(obj => {
                obj.position.x += obj.userData.driftX;
                obj.position.y += Math.sin(time + obj.userData.floatOffset) * obj.userData.floatSpeed;
                
                // Infinite wrap around logic
                if (obj.position.x > 25) obj.position.x = -25;
                if (obj.position.x < -25) obj.position.x = 25;
            });

            renderer.render(scene, camera);
        }
        animate();
    </script>
</body>
</html>
"""

st.markdown(premium_css, unsafe_allow_html=True)
components.html(three_js_code, height=100)

st.markdown("""
<div style="display: flex; align-items: center; gap: 20px; margin-top: 10px; margin-bottom: 20px;">
    <svg width="60" height="60" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 0 15px rgba(244,63,94,0.6));">
        <path d="M50 5 L90 25 L90 75 L50 95 L10 75 L10 25 Z" fill="url(#grad)" stroke="#fbcfe8" stroke-width="2"/>
        <path d="M50 5 L50 45 L90 25 M50 45 L10 25 M50 45 L50 95" stroke="#fbcfe8" stroke-width="2"/>
        <circle cx="50" cy="45" r="5" fill="#fff" />
        <defs>
            <linearGradient id="grad" x1="0" y1="0" x2="100" y2="100">
                <stop offset="0%" stop-color="#f43f5e" stop-opacity="0.9"/>
                <stop offset="100%" stop-color="#d946ef" stop-opacity="0.3"/>
            </linearGradient>
        </defs>
    </svg>
    <h1 style="margin: 0; padding: 0; font-family: 'Outfit', sans-serif;">TrueFit Intelligent Ranker</h1>
</div>
""", unsafe_allow_html=True)
st.markdown("""
Welcome to the **Premium Sandbox Experience**.
This pipeline runs the exact **7-stage intelligent ranking system** with live honeypot detection, TF-IDF semantic matching, and 5-dimensional rule-based scoring.
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
            "candidate_id": candidate_id,
            "rank": rank,
            "score": f"{res['score']:.4f}",
            "reasoning": reasoning
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
st.markdown("**Built for Redrob AI Challenge by Purjeet (Team HaXker)** | Engine: Pure Python + Scikit-Learn | Deterministic Rule-based Scoring")
