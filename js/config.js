export const CONFIG = {
  defaultWeights: { semantic: 35, career: 25, activity: 20, skills: 12, culture: 8 },
  topK: 20,
  scoreRingRadius: 22,
  scoreRingCircumference: 2 * Math.PI * 22,
};

export const WEIGHT_LABELS = {
  semantic: 'Semantic',
  career: 'Career',
  activity: 'Activity',
  skills: 'Skills',
  culture: 'Culture'
};

export const WEIGHT_COLORS = {
  semantic: '#7C6DFA',
  career: '#60A5FA',
  activity: '#2DD4BF',
  skills: '#34D399',
  culture: '#FBBF24'
};

export const AVATAR_COLORS = [
  '#7C6DFA','#34D399','#FBBF24','#F87171','#60A5FA','#2DD4BF',
  '#A594FF','#FB923C','#E879F9','#38BDF8','#4ADE80','#FCD34D'
];

export const SKILL_ALIASES = {
  'node.js': ['nodejs', 'node', 'node.js'],
  'nodejs': ['node.js', 'node', 'nodejs'],
  'node': ['node.js', 'nodejs', 'node'],
  'react.js': ['reactjs', 'react', 'react.js'],
  'reactjs': ['react.js', 'react', 'reactjs'],
  'react': ['react.js', 'reactjs', 'react'],
  'vue.js': ['vuejs', 'vue', 'vue.js'],
  'vuejs': ['vue.js', 'vue', 'vuejs'],
  'vue': ['vue.js', 'vuejs', 'vue'],
  'angular.js': ['angularjs', 'angular'],
  'angularjs': ['angular.js', 'angular'],
  'angular': ['angular.js', 'angularjs'],
  'javascript': ['js', 'ecmascript', 'es6'],
  'js': ['javascript', 'ecmascript', 'es6'],
  'typescript': ['ts'],
  'ts': ['typescript'],
  'python': ['py', 'python3'],
  'py': ['python', 'python3'],
  'machine learning': ['ml', 'machine-learning'],
  'ml': ['machine learning', 'machine-learning'],
  'deep learning': ['dl', 'deep-learning'],
  'dl': ['deep learning', 'deep-learning'],
  'natural language processing': ['nlp'],
  'nlp': ['natural language processing'],
  'artificial intelligence': ['ai'],
  'ai': ['artificial intelligence'],
  'amazon web services': ['aws'],
  'aws': ['amazon web services'],
  'google cloud platform': ['gcp', 'google cloud'],
  'gcp': ['google cloud platform', 'google cloud'],
  'kubernetes': ['k8s'],
  'k8s': ['kubernetes'],
  'postgresql': ['postgres', 'pg'],
  'postgres': ['postgresql', 'pg'],
  'mongodb': ['mongo'],
  'mongo': ['mongodb'],
  'tensorflow': ['tf'],
  'tf': ['tensorflow'],
  'scikit-learn': ['sklearn'],
  'sklearn': ['scikit-learn'],
  'large language models': ['llm', 'llms'],
  'llm': ['large language models', 'llms'],
  'llms': ['large language models', 'llm'],
  'fine-tuning llms': ['llm fine-tuning', 'fine tuning llms'],
  'ci/cd': ['cicd', 'ci cd'],
  'devops': ['dev ops', 'dev-ops'],
};

export const SKILL_ONTOLOGY = {
  'deep_learning': ['pytorch', 'tensorflow', 'keras', 'jax', 'deep learning'],
  'big_data': ['spark', 'pyspark', 'databricks', 'hadoop', 'kafka', 'flink', 'beam', 'data pipelines'],
  'frontend': ['react', 'react.js', 'next.js', 'nextjs', 'typescript', 'ts', 'angular', 'vue', 'vue.js', 'javascript', 'js', 'tailwind', 'tailwindcss', 'material ui', 'mui', 'svelte'],
  'databases': ['sql', 'postgresql', 'postgres', 'mysql', 'mongodb', 'mongo', 'redis', 'elasticsearch', 'milvus', 'pinecone', 'vector db', 'vector database', 'chromadb', 'weaviate'],
  'devops': ['aws', 'gcp', 'azure', 'docker', 'kubernetes', 'k8s', 'terraform', 'ci/cd', 'jenkins', 'github actions', 'gitlab', 'prometheus', 'grafana', 'datadog', 'elk', 'splunk'],
  'ai_nlp': ['nlp', 'natural language processing', 'llm', 'llms', 'large language models', 'langchain', 'llamaindex', 'transformers', 'gpt', 'bert', 'rag', 'fine-tuning', 'fine tuning', 'lora', 'gans', 'tts', 'computer vision'],
  'pm_business': ['product management', 'project management', 'stakeholder management', 'seo', 'content writing', 'marketing', 'sales', 'accounting', 'agile', 'scrum', 'jira'],
  'mobile': ['android', 'ios'],
  'hardware_eng': ['solidworks', 'ansys']
};

export const JD_PRESETS = [
  {
    label: '🤖 Senior ML Engineer',
    jd: `Senior Machine Learning Engineer — FinTech Startup (Series B)

We're looking for a Senior ML Engineer to join our core AI team building next-generation fraud detection and credit risk models.

REQUIRED SKILLS:
- Python, PyTorch or TensorFlow
- NLP, deep learning, transformer architectures
- Experience with ML model deployment (MLflow, BentoML, or similar)
- Strong understanding of statistical modeling and feature engineering
- 5+ years of experience in ML/AI roles

PREFERRED:
- Experience with large language models (LLMs) and fine-tuning
- Knowledge of Spark, Airflow for data pipeline orchestration
- Cloud platforms (AWS, GCP, or Azure)
- Experience in fintech or financial services domain
- Leadership experience, mentoring junior engineers

ABOUT THE ROLE:
- Hybrid work mode (Bangalore preferred)
- Lead a team of 3-4 ML engineers
- Ship production ML systems serving 10M+ predictions/day
- Collaborate with data engineering and product teams`
  },
  {
    label: '💻 Full Stack Developer',
    jd: `Full Stack Developer — SaaS Platform (Growth Stage)

We're hiring a Full Stack Developer to build and scale our B2B SaaS platform used by 500+ enterprise clients.

REQUIRED SKILLS:
- React or Angular frontend development
- Node.js or Python backend development
- SQL databases (PostgreSQL, MySQL)
- RESTful API design and GraphQL
- 3+ years of experience in full-stack development

PREFERRED:
- TypeScript proficiency
- Docker, Kubernetes, CI/CD pipelines
- Redis, message queues (Kafka, RabbitMQ)
- AWS or GCP cloud services
- Experience with agile/scrum methodologies

ABOUT THE ROLE:
- Remote-first, flexible hours
- Work on high-scale systems (100K+ daily active users)
- Strong focus on code quality, testing, and documentation
- Competitive salary: 18-35 LPA`
  },
  {
    label: '🔧 Data Engineer',
    jd: `Senior Data Engineer — Enterprise Analytics (Fortune 500)

Join our data platform team to build and maintain mission-critical data infrastructure supporting analytics and ML workloads at scale.

REQUIRED SKILLS:
- Apache Spark, PySpark for large-scale data processing
- SQL expertise (advanced queries, optimization, warehouse design)
- Apache Airflow or similar orchestration tools
- Python programming
- 4+ years of data engineering experience

PREFERRED:
- Databricks, Snowflake, or BigQuery experience
- Kafka, streaming data architectures
- AWS (S3, Glue, Redshift) or GCP (BigQuery, Dataflow)
- Data modeling, star/snowflake schema design
- Experience with dbt for data transformation

ABOUT THE ROLE:
- Onsite position in Bangalore or Hyderabad
- Processing 500GB+ daily data volumes
- Building real-time and batch pipelines
- Cross-functional work with data science and analytics teams`
  },
  {
    label: '📊 AI Product Manager',
    jd: `AI Product Manager — AI-First SaaS Company

We're looking for a Product Manager with deep AI/ML understanding to drive our intelligent automation product line.

REQUIRED SKILLS:
- 5+ years of product management experience
- Strong understanding of AI/ML concepts and capabilities
- Data-driven decision making and analytics
- Stakeholder management and cross-functional leadership
- Experience shipping B2B SaaS products

PREFERRED:
- Technical background (computer science, engineering)
- Experience with NLP, computer vision, or recommendation systems
- Familiarity with agile methodologies and product analytics tools
- Understanding of AI ethics and responsible AI practices
- MBA or equivalent business education

ABOUT THE ROLE:
- Hybrid work (Mumbai or Bangalore)
- Own the product roadmap for our AI-powered platform
- Work directly with ML engineers and data scientists
- Report to VP of Product`
  }
];

export const STOPWORDS = new Set([
  'a','an','the','and','or','but','in','on','at','to','for','of','with','by',
  'from','is','are','was','were','be','been','being','have','has','had','do',
  'does','did','will','would','could','should','may','might','shall','can',
  'not','no','nor','so','if','then','than','too','very','just','about',
  'above','after','again','all','also','am','any','because','before',
  'between','both','during','each','few','further','get','got','her','here',
  'him','his','how','i','into','it','its','let','me','more','most','my',
  'myself','now','only','other','our','out','own','same','she','some',
  'such','that','their','them','these','they','this','those','through',
  'under','until','up','us','we','what','when','where','which','while',
  'who','whom','why','you','your','re','ve','ll','t','s','d','m',
  'experience','work','working','team','role','company','looking',
  'join','help','build','strong','ability','using','used','use',
]);
