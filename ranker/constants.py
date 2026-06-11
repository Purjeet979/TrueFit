"""
Constants for the TrueFit ranking engine.
Skill aliases, consulting firms, JD-specific signals, and scoring weights.
"""

# ============================================================================
# The actual JD text (Senior AI Engineer — Founding Team at Redrob AI)
# ============================================================================
JD_TEXT = """
Senior AI Engineer — Founding Team
Company: Redrob AI (Series A AI-native talent intelligence platform)
Location: Pune/Noida, India (Hybrid — flexible cadence)
Experience Required: 5–9 years

Required Skills:
- Production experience with embeddings-based retrieval systems (sentence-transformers, OpenAI embeddings, BGE, E5, or similar)
- Production experience with vector databases or hybrid search infrastructure (Pinecone, Weaviate, Qdrant, Milvus, OpenSearch, Elasticsearch, FAISS)
- Strong Python
- Evaluation frameworks for ranking systems (NDCG, MRR, MAP, A/B testing)

Preferred Skills:
- LLM fine-tuning experience (LoRA, QLoRA, PEFT)
- Experience with learning-to-rank models (XGBoost-based or neural)
- Prior exposure to HR-tech, recruiting tech, or marketplace products
- Background in distributed systems or large-scale inference optimization
- Open-source contributions in the AI/ML space

Key requirements:
- 5-9 years experience in applied ML/AI at product companies
- Shipped production ML systems to real users
- Deep technical depth in embeddings, retrieval, ranking, LLMs, fine-tuning
- Scrappy product-engineering attitude — willing to ship fast
- Located in or willing to relocate to Pune/Noida area
- Prefers sub-30-day notice period
"""

# ============================================================================
# Scoring weights — tuned for this specific JD
# ============================================================================
SCORING_WEIGHTS = {
    "role_fit": 0.30,        # Title alignment, seniority, production experience
    "skills_depth": 0.25,    # Specific skill matching for embeddings/retrieval/Python
    "career_quality": 0.20,  # Product company experience, trajectory, tenure
    "behavioral": 0.15,      # Activity, response rate, open-to-work, verification
    "cultural": 0.10,        # Location, company stage, domain consistency
}

# ============================================================================
# Consulting / Services firms (JD explicitly disqualifies entire-career-here)
# ============================================================================
CONSULTING_FIRMS = {
    "tcs", "tata consultancy services", "infosys", "wipro", "accenture",
    "cognizant", "capgemini", "hcl", "hcl technologies", "tech mahindra",
    "mindtree", "l&t infotech", "lti", "ltimindtree", "mphasis",
    "hexaware", "cyient", "persistent systems", "zensar",
    "atos", "dxc technology", "ibm services", "deloitte consulting",
}

# ============================================================================
# Fictional / dataset-specific company names (not consulting penalties)
# ============================================================================
FICTIONAL_COMPANIES = {
    "dunder mifflin", "globex inc", "initech", "stark industries",
    "wayne enterprises", "acme corp", "umbrella corp", "soylent corp",
    "oscorp", "hooli", "pied piper", "piedpiper",
}

# ============================================================================
# Non-technical titles that should NOT rank high for an AI Engineer role
# ============================================================================
NON_TECHNICAL_TITLES = {
    "marketing manager", "hr manager", "operations manager", "accountant",
    "sales executive", "customer support", "content writer",
    "graphic designer", "business analyst", "project manager",
    "mechanical engineer", "civil engineer",
}

# ============================================================================
# Titles that indicate strong ML/AI/Engineering fit
# ============================================================================
STRONG_FIT_TITLES = {
    "machine learning engineer", "ml engineer", "senior ml engineer",
    "ai engineer", "senior ai engineer", "data scientist",
    "senior data scientist", "research engineer", "applied scientist",
    "nlp engineer", "deep learning engineer", "software engineer",
    "senior software engineer", "staff engineer", "principal engineer",
    "backend engineer", "data engineer", "senior data engineer",
    "platform engineer", "infrastructure engineer",
    "tech lead", "engineering manager",
}

# Title keywords for partial matching
STRONG_FIT_TITLE_KEYWORDS = [
    "machine learning", "ml ", "ai ", "data scien", "deep learning",
    "nlp", "software engineer", "backend engineer", "data engineer",
    "platform engineer", "research engineer", "applied scientist",
    "tech lead", "staff engineer", "principal engineer",
    "senior engineer", "infrastructure",
]

WEAK_FIT_TITLE_KEYWORDS = [
    "junior", "intern", "fresher", "trainee", "associate",
]

# ============================================================================
# Skill aliases — canonical form → alternatives
# ============================================================================
SKILL_ALIASES = {
    "python": ["py", "python3"],
    "pytorch": ["torch"],
    "tensorflow": ["tf", "keras"],
    "scikit-learn": ["sklearn", "scikit learn"],
    "nlp": ["natural language processing"],
    "machine learning": ["ml"],
    "deep learning": ["dl"],
    "artificial intelligence": ["ai"],
    "large language models": ["llm", "llms"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform", "google cloud"],
    "kubernetes": ["k8s"],
    "docker": [],
    "postgresql": ["postgres", "pg"],
    "mongodb": ["mongo"],
    "node.js": ["nodejs", "node"],
    "react": ["react.js", "reactjs"],
    "javascript": ["js"],
    "typescript": ["ts"],
    "elasticsearch": ["elastic search", "opensearch"],
    "spark": ["pyspark", "apache spark"],
    "airflow": ["apache airflow"],
    "kafka": ["apache kafka"],
    "faiss": [],
    "pinecone": [],
    "weaviate": [],
    "qdrant": [],
    "milvus": [],
    "chromadb": ["chroma"],
    "langchain": [],
    "llamaindex": ["llama index"],
    "transformers": ["huggingface transformers", "hf transformers"],
    "sentence-transformers": [
        "sentence transformers", "sbert",
        "bge", "bge-m3", "bge-large", "bge-base",         # Beijing Academy of AI
        "e5", "e5-large", "e5-base", "multilingual-e5",   # Microsoft E5
        "ada-002", "text-embedding-ada", "openai embeddings",  # OpenAI
        "instructor", "instructor-xl",                    # HKUNLP Instructor
    ],
    "bert": [],
    "gpt": [],
    "rag": ["retrieval augmented generation"],
    "fine-tuning": ["fine tuning", "finetuning"],
    "lora": ["qlora", "peft"],
    "xgboost": ["xgb"],
    "vector database": ["vector db", "vector store", "vector index"],
    "embeddings": ["embedding", "text embeddings"],
    "ranking": ["learning to rank", "ltr"],
    "information retrieval": ["ir"],
    "recommendation systems": ["recommender systems", "recommendations"],
    "mlflow": [],
    "bentoml": [],
    "mlops": [],
    "ci/cd": ["cicd"],
    "graphql": [],
    "fastapi": [],
    "django": [],
    "flask": [],
    "redis": [],
    "sql": ["mysql"],
    "dbt": [],
    "databricks": [],
    "snowflake": [],
    "hadoop": [],
    "feature engineering": [],
    "statistical modeling": ["statistics"],
    "a/b testing": ["ab testing", "experimentation"],
    "ndcg": ["normalized discounted cumulative gain"],
    "mrr": ["mean reciprocal rank"],
    "map": ["mean average precision"],
    "hybrid search": [
        "hybrid retrieval", "dense-sparse retrieval", "sparse-dense",
        "bm25+embeddings", "reciprocal rank fusion", "rrf",
        "dense retrieval", "sparse retrieval",
    ],
    "inference optimization": [
        "model optimization", "quantization", "onnx", "tensorrt",
        "trt", "int8", "fp16", "model compression", "distillation",
    ],
    "distributed systems": [
        "distributed computing", "large scale systems", "horizontal scaling",
        "sharding", "distributed training", "distributed inference",
    ],
    "computer vision": ["cv"],
    "gans": ["generative adversarial"],
    "data pipelines": ["etl", "data pipeline"],
}

# ============================================================================
# JD-specific required skills (weighted highest)
# ============================================================================
JD_REQUIRED_SKILLS = [
    "python",
    "embeddings",
    "sentence-transformers",
    "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "elasticsearch", "opensearch",
    "ranking",
    "information retrieval",
    "ndcg", "mrr", "map",   # All three eval metrics explicitly in JD
    "a/b testing",
    "hybrid search",           # JD Week 4-8 mandate
]

JD_PREFERRED_SKILLS = [
    "lora", "fine-tuning", "peft",
    "xgboost", "learning to rank",
    "distributed systems",          # JD preferred
    "inference optimization",       # JD preferred (large-scale inference)
    "recommendation systems",
    "mlops",                        # Production deployment infra
]

# Core AI/ML skills that indicate genuine technical depth
CORE_AI_SKILLS = {
    "python", "pytorch", "tensorflow", "scikit-learn", "nlp",
    "machine learning", "deep learning", "transformers",
    "bert", "gpt", "rag", "langchain", "llamaindex",
    "embeddings", "sentence-transformers", "fine-tuning", "lora",
    "faiss", "pinecone", "weaviate", "qdrant", "milvus",
    "vector database", "elasticsearch",
    "spark", "airflow", "kafka", "sql",
    "mlflow", "mlops", "docker", "kubernetes",
    "xgboost", "feature engineering", "statistical modeling",
    "recommendation systems", "information retrieval",
    "computer vision", "gans", "data pipelines",
    "ranking", "ndcg", "a/b testing",
    "fastapi", "flask", "django",
    "redis", "postgresql", "mongodb",
    "aws", "gcp",
}

# Skills that indicate only shallow/trendy AI exposure
SHALLOW_AI_INDICATORS = {
    "seo", "content writing", "marketing", "sales", "accounting",
    "photoshop", "figma", "powerpoint", "excel",
    "solidworks", "ansys", "six sigma", "sap",
}

# ============================================================================
# Production experience indicators in career descriptions
# ============================================================================
PRODUCTION_INDICATORS = [
    "production", "deployed", "shipped", "scale", "scaled",
    "users", "traffic", "pipeline", "real-time", "realtime",
    "latency", "throughput", "availability", "uptime",
    "microservices", "api", "infrastructure", "monitoring",
    "a/b test", "ab test", "experiment",
    "million", "billion", "10k", "100k", "1m",
]

ML_PRODUCTION_INDICATORS = [
    "model serving", "model deployment", "inference",
    "embedding", "retrieval", "ranking", "recommendation",
    "search", "vector", "index", "features",
    "training pipeline", "data pipeline", "ml pipeline",
    "mlflow", "mlops", "bentoml", "sagemaker",
    "fine-tun", "fine tun",
]

LEADERSHIP_INDICATORS = [
    "led", "lead", "managed", "mentor", "team of",
    "oversaw", "owned", "stakeholder", "architecture",
    "system design", "scaling",
]

# ============================================================================
# Location preferences from the JD
# ============================================================================
PREFERRED_LOCATIONS = [
    "pune", "noida", "hyderabad", "mumbai", "delhi",
    "gurgaon", "gurugram", "bangalore", "bengaluru",
    "chennai",
]

INDIA_LOCATIONS = PREFERRED_LOCATIONS + [
    "kolkata", "ahmedabad", "jaipur", "lucknow", "chandigarh",
    "kochi", "thiruvananthapuram", "indore", "bhopal",
    "coimbatore", "nagpur", "surat", "vadodara",
]

# ============================================================================
# Seniority level keywords for title analysis
# ============================================================================
SENIORITY_LEVELS = {
    "intern": 0, "trainee": 0,
    "junior": 1, "jr": 1, "fresher": 1,
    "associate": 2,
    "analyst": 3,
    "engineer": 4, "developer": 4, "scientist": 4,
    "senior": 5, "sr": 5,
    "lead": 6, "staff": 6,
    "principal": 7,
    "manager": 7, "director": 8,
    "vp": 9, "head": 9,
    "cto": 10, "ceo": 10,
}
