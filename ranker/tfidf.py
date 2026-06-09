"""
TF-IDF vectorization and cosine similarity for candidate-JD matching.
Pure Python implementation — no external dependencies.
Optimized for 100K candidates within the 5-minute CPU constraint.
"""

import math
import re
from collections import Counter
from ranker.utils import setup_logger

logger = setup_logger(__name__)

# Stopwords for English text
STOPWORDS = frozenset([
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "not", "no", "nor",
    "so", "if", "then", "than", "too", "very", "just", "about", "above",
    "after", "again", "all", "also", "am", "any", "because", "before",
    "between", "both", "during", "each", "few", "further", "get", "got",
    "her", "here", "him", "his", "how", "i", "into", "it", "its", "let",
    "me", "more", "most", "my", "myself", "now", "only", "other", "our",
    "out", "own", "same", "she", "some", "such", "that", "their", "them",
    "these", "they", "this", "those", "through", "under", "until", "up",
    "us", "we", "what", "when", "where", "which", "while", "who", "whom",
    "why", "you", "your", "re", "ve", "ll", "t", "s", "d", "m",
    "experience", "work", "working", "team", "role", "company", "looking",
    "join", "help", "build", "strong", "ability", "using", "used", "use",
])

# Words to protect from stemming (technical terms that end in common suffixes)
STEM_PROTECT = frozenset([
    "kubernetes", "pandas", "keras", "jenkins", "redis", "postgres", "aws",
    "gans", "llms", "transformers", "series", "analysis", "models",
    "systems", "services", "queries", "pipelines", "architectures",
    "databases", "apis", "microservices", "embeddings", "rankings",
    "faiss", "milvus", "process", "metrics", "features",
])


def simple_stem(word):
    """Lightweight English stemmer (suffix stripping)."""
    if len(word) <= 2 or word in STEM_PROTECT:
        return word

    if word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "i"
    elif word.endswith("ss"):
        pass
    elif word.endswith("s") and not word.endswith(("us", "as", "is", "os")):
        word = word[:-1]

    if word.endswith("eed"):
        if len(word) > 4:
            word = word[:-1]
    elif word.endswith("ing"):
        if len(word) > 5:
            word = word[:-3]
            if word.endswith(("at", "bl", "iz")):
                word += "e"
    elif word.endswith("ed"):
        if len(word) > 4:
            word = word[:-2]
            if word.endswith(("at", "bl", "iz")):
                word += "e"

    return word


def tokenize(text):
    """Tokenize text: lowercase, remove punctuation, remove stopwords, stem."""
    text = re.sub(r'[^a-z0-9\s\-./+#]', ' ', text.lower())
    tokens = text.split()
    return [
        simple_stem(t) for t in tokens
        if len(t) > 1 and t not in STOPWORDS
    ]


from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def compute_tfidf_similarity(jd_text, candidate_texts, top_k=500):
    """
    Compute TF-IDF cosine similarity between a JD and all candidates using scikit-learn.

    This is highly optimized:
    - Only builds vocabulary from JD terms for speed and memory efficiency
    - Uses sparse matrix operations and numpy for fast cosine similarity

    Args:
        jd_text: The job description text
        candidate_texts: List of (index, text) tuples
        top_k: Number of top candidates to return

    Returns:
        List of (candidate_index, similarity_score) sorted by similarity desc
    """
    jd_tokens = tokenize(jd_text)
    jd_vocab = set(jd_tokens)
    
    if not jd_vocab:
        return []

    # Prepare corpus: candidates + JD
    corpus = [text for _, text in candidate_texts]
    corpus.append(jd_text)
    
    # Initialize TF-IDF Vectorizer with custom tokenizer and JD vocabulary
    # This ensures we only care about JD terms and ignore the rest
    vectorizer = TfidfVectorizer(
        tokenizer=tokenize,
        vocabulary=list(jd_vocab),
        token_pattern=None, # Suppress warning since we use a custom tokenizer
        norm='l2',
        use_idf=True,
        smooth_idf=True,
        sublinear_tf=True # Use logarithmic tf, similar to original logic
    )

    # Compute TF-IDF matrix for the entire corpus
    tfidf_matrix = vectorizer.fit_transform(corpus)
    
    # The last row is the JD vector
    jd_vector = tfidf_matrix[-1:]
    candidate_vectors = tfidf_matrix[:-1]

    # Compute cosine similarities between the JD and all candidates
    similarities = cosine_similarity(jd_vector, candidate_vectors).flatten()

    # Get the indices of the top_k candidates
    # argpartition is faster than full sort for getting top K
    k = min(top_k, len(similarities))
    if k == 0:
        return []
        
    top_indices = np.argpartition(similarities, -k)[-k:]
    
    # Sort the top K indices by similarity score descending
    top_indices_sorted = top_indices[np.argsort(-similarities[top_indices])]

    # Build the final list of (candidate_index, similarity_score)
    results = []
    for idx in top_indices_sorted:
        cand_idx = candidate_texts[idx][0]
        score = float(similarities[idx])
        results.append((cand_idx, score))

    logger.debug(f"Computed TF-IDF similarity for {len(candidate_texts)} candidates")
    return results

class TFIDFCache:
    """Cache TF-IDF vocabulary and vectorizer to avoid recomputation"""
    
    def __init__(self):
        self.vectorizer = None
        self.vocabulary = None
        self.last_jd_text = None
        self.jd_vector = None
        logger.debug("Initialized TFIDFCache")
    
    def compute_with_caching(self, jd_text: str, candidate_texts: list, top_k: int = 500):
        """
        Compute TF-IDF similarity with caching.
        If JD text hasn't changed, reuse vectorizer.
        """
        if jd_text == self.last_jd_text and self.vectorizer is not None:
            logger.debug("Reusing cached TF-IDF vectorizer")
            
            if not candidate_texts:
                return []
                
            corpus = [text for _, text in candidate_texts]
            candidate_vectors = self.vectorizer.transform(corpus)
            similarities = cosine_similarity(self.jd_vector, candidate_vectors).flatten()
            
            k = min(top_k, len(similarities))
            if k == 0: return []
            top_indices = np.argpartition(similarities, -k)[-k:]
            top_indices_sorted = top_indices[np.argsort(-similarities[top_indices])]
            
            results = []
            for idx in top_indices_sorted:
                cand_idx = candidate_texts[idx][0]
                score = float(similarities[idx])
                results.append((cand_idx, score))
            return results
            
        else:
            logger.debug("Computing new TF-IDF vectorizer")
            jd_tokens = tokenize(jd_text)
            jd_vocab = set(jd_tokens)
            
            if not jd_vocab:
                return []
                
            corpus = [text for _, text in candidate_texts]
            corpus.append(jd_text)
            
            self.vectorizer = TfidfVectorizer(
                tokenizer=tokenize,
                vocabulary=list(jd_vocab),
                token_pattern=None,
                norm='l2',
                use_idf=True,
                smooth_idf=True,
                sublinear_tf=True
            )
            
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            self.jd_vector = tfidf_matrix[-1:]
            self.last_jd_text = jd_text
            
            candidate_vectors = tfidf_matrix[:-1]
            similarities = cosine_similarity(self.jd_vector, candidate_vectors).flatten()
            
            k = min(top_k, len(similarities))
            if k == 0: return []
            top_indices = np.argpartition(similarities, -k)[-k:]
            top_indices_sorted = top_indices[np.argsort(-similarities[top_indices])]
            
            results = []
            for idx in top_indices_sorted:
                cand_idx = candidate_texts[idx][0]
                score = float(similarities[idx])
                results.append((cand_idx, score))
            return results

