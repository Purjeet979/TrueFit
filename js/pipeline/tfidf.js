import { tokenize } from '../utils.js';
import { SKILL_ALIASES } from '../config.js';

function skillAliasText(skillName) {
  const name = (skillName || '').toLowerCase().trim();
  const aliases = SKILL_ALIASES[name] || [];
  return [name, ...aliases].join(' ');
}

function candidateToSearchText(candidate) {
  const skillNames = (candidate.skills || []).map(s => s.name || '');
  const weightedSkills = skillNames.flatMap(name => [
    name,
    name,
    skillAliasText(name),
  ]);

  const parts = [
    candidate.profile?.summary || '',
    candidate.profile?.headline || '',
    candidate.profile?.current_title || '',
    candidate.profile?.current_industry || '',
    weightedSkills.join(' '),
    (candidate.career_history || []).map(h => [
      h.title || '',
      h.industry || '',
      h.description || '',
    ].join(' ')).join(' '),
    (candidate.education || []).map(e => [
      e.degree || '',
      e.field_of_study || '',
    ].join(' ')).join(' '),
  ];

  return parts.join(' ');
}

export function tfidfVectorise(jdText, pool) {
  const jdAliasText = Object.entries(SKILL_ALIASES)
    .filter(([skill, aliases]) => {
      const text = jdText.toLowerCase();
      return text.includes(skill) || aliases.some(alias => text.includes(alias));
    })
    .flatMap(([skill, aliases]) => [skill, ...aliases])
    .join(' ');

  const jdTokens = tokenize(`${jdText} ${jdAliasText}`);
  const docs = pool.map(c => tokenize(candidateToSearchText(c)));

  // Build vocabulary
  const vocabulary = new Set();
  jdTokens.forEach(t => vocabulary.add(t));
  docs.forEach(d => d.forEach(t => vocabulary.add(t)));
  const vocabArray = [...vocabulary];
  const vocabIndex = {};
  vocabArray.forEach((t, i) => vocabIndex[t] = i);

  // Document frequency
  const N = docs.length + 1;
  const df = new Float32Array(vocabArray.length);
  const allDocs = [jdTokens, ...docs];
  allDocs.forEach(doc => {
    const seen = new Set();
    doc.forEach(t => {
      if (!seen.has(t)) {
        df[vocabIndex[t]]++;
        seen.add(t);
      }
    });
  });

  // IDF
  const idf = new Float32Array(vocabArray.length);
  for (let i = 0; i < vocabArray.length; i++) {
    idf[i] = Math.log((N + 1) / (df[i] + 1)) + 1;
  }

  // TF-IDF vectors
  function buildVector(tokens) {
    const tf = {};
    tokens.forEach(t => { tf[t] = (tf[t] || 0) + 1; });
    const vec = {};
    const maxTf = Math.max(...Object.values(tf), 1);
    for (const [term, count] of Object.entries(tf)) {
      if (vocabIndex[term] !== undefined) {
        vec[term] = (0.5 + 0.5 * count / maxTf) * idf[vocabIndex[term]];
      }
    }
    return vec;
  }

  const jdVector = buildVector(jdTokens);
  const candidateVectors = docs.map(d => buildVector(d));

  return { jdVector, candidateVectors, vocabulary: vocabArray };
}
