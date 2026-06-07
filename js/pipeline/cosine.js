export function cosineSimilaritySearch(jdVec, candidateVecs, vocabulary) {
  const jdNorm = Math.sqrt(Object.values(jdVec).reduce((s, v) => s + v * v, 0)) || 1;

  return candidateVecs.map((cVec, i) => {
    let dot = 0;
    let cNorm = 0;
    // Iterate shared keys
    for (const term in jdVec) {
      if (cVec[term]) dot += jdVec[term] * cVec[term];
    }
    for (const term in cVec) {
      cNorm += cVec[term] * cVec[term];
    }
    cNorm = Math.sqrt(cNorm) || 1;
    return { index: i, similarity: dot / (jdNorm * cNorm) };
  });
}
