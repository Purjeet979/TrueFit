import { CONFIG } from './config.js';
import { sleep } from './utils.js';
import { nlpParse } from './pipeline/nlpParse.js';
import { tfidfVectorise } from './pipeline/tfidf.js';
import { cosineSimilaritySearch } from './pipeline/cosine.js';
import { multiSignalReRank } from './pipeline/rerank.js';
import { generateNarrative } from './pipeline/narrative.js';
import { applyFilters } from './filters.js';
import { renderPresets, renderWeightSliders, renderResults, renderJDInsights } from './ui.js';

// Global application state
let candidates = [];
let currentResults = [];
let currentSort = 'overall';
let weights = { ...CONFIG.defaultWeights };
let jdSignals = null;

document.addEventListener('DOMContentLoaded', async () => {
  renderPresets((jdText) => {
    // Optionally trigger something when preset is selected
  });
  renderWeightSliders(weights);
  bindEvents();
  await loadCandidates();
});

async function loadCandidates() {
  const el = document.getElementById('engine-label');
  el.textContent = 'Loading candidate pool…';

  const paths = [
    './sample_candidates.json',
    './[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/sample_candidates.json',
  ];

  for (const path of paths) {
    try {
      const res = await fetch(path);
      if (res.ok) {
        candidates = await res.json();
        populateLocationFilter();
        el.textContent = `Edge AI Engine Ready · ${candidates.length} profiles`;
        return;
      }
    } catch (e) { /* try next */ }
  }

  el.textContent = 'Could not load data — serve via HTTP';
  document.getElementById('status-dot').style.background = 'var(--red)';
}

function populateLocationFilter() {
  const locations = [...new Set(candidates.map(c => {
    const loc = c.profile.location;
    return loc.includes(',') ? loc.split(',').pop().trim() : loc;
  }))].sort();
  
  const sel = document.getElementById('filter-location');
  locations.forEach(loc => {
    const opt = document.createElement('option');
    opt.value = loc;
    opt.textContent = loc;
    sel.appendChild(opt);
  });
}

function bindEvents() {
  document.getElementById('search-btn').addEventListener('click', runPipeline);

  // Open-to-work toggle
  const otwToggle = document.getElementById('filter-otw');
  otwToggle.addEventListener('click', function() {
    this.classList.toggle('active');
    this.setAttribute('aria-checked', this.classList.contains('active'));
  });
  otwToggle.addEventListener('keydown', function(e) {
    if (e.key === ' ' || e.key === 'Enter') {
      e.preventDefault();
      this.click();
    }
  });

  // Sort buttons
  document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentSort = btn.dataset.sort;
      if (currentResults.length) {
        renderResults(sortResults(currentResults));
      }
    });
  });
}

async function runPipeline() {
  const jdText = document.getElementById('jd-input').value.trim();
  if (!jdText) {
    document.getElementById('jd-input').style.borderColor = 'var(--red)';
    setTimeout(() => document.getElementById('jd-input').style.borderColor = '', 1500);
    return;
  }
  if (!candidates.length) return;

  const btn = document.getElementById('search-btn');
  const btnText = document.getElementById('search-btn-text');
  btn.disabled = true;
  btnText.textContent = 'Processing…';

  const progressContainer = document.getElementById('progress-container');
  const progressFill = document.getElementById('progress-fill');
  progressContainer.classList.add('active');
  progressFill.style.width = '0%';

  const steps = document.querySelectorAll('.pipeline-step');
  steps.forEach(s => { s.classList.remove('active', 'done'); });

  const pipelineStart = performance.now();

  // Small delay to let UI update
  await sleep(50);

  // Stage 1: NLP Parse
  setStage(steps, 0, 'active');
  progressFill.style.width = '10%';
  await sleep(80);
  jdSignals = nlpParse(jdText);
  renderJDInsights(jdSignals);
  setStage(steps, 0, 'done');

  // Stage 2: TF-IDF Vectorise
  setStage(steps, 1, 'active');
  progressFill.style.width = '30%';
  await sleep(80);
  const { jdVector, candidateVectors, vocabulary } = tfidfVectorise(jdText, candidates);
  setStage(steps, 1, 'done');

  // Stage 3: Cosine Similarity Search
  setStage(steps, 2, 'active');
  progressFill.style.width = '50%';
  await sleep(80);
  const similarities = cosineSimilaritySearch(jdVector, candidateVectors, vocabulary);
  setStage(steps, 2, 'done');

  // Stage 4: Multi-Signal Re-Rank
  setStage(steps, 3, 'active');
  progressFill.style.width = '70%';
  await sleep(80);

  // Apply hard filters first
  const filtered = applyFilters(candidates);
  const rankedResults = multiSignalReRank(filtered, similarities, jdSignals, weights, candidates);
  setStage(steps, 3, 'done');

  // Stage 5: Narrative Generation
  setStage(steps, 4, 'active');
  progressFill.style.width = '90%';
  await sleep(80);
  
  let baselineDate = new Date("2026-01-01");
  let maxActiveTime = 0;
  candidates.forEach(c => {
    if (c.redrob_signals && c.redrob_signals.last_active_date) {
      const d = new Date(c.redrob_signals.last_active_date).getTime();
      if (d > maxActiveTime) maxActiveTime = d;
    }
  });
  if (maxActiveTime > 0) {
    baselineDate = new Date(maxActiveTime);
  }

  rankedResults.forEach(r => {
    r.narrative = generateNarrative(r, jdSignals, baselineDate);
  });
  setStage(steps, 4, 'done');
  progressFill.style.width = '100%';

  const pipelineTime = performance.now() - pipelineStart;

  // Update stats
  document.getElementById('stat-scanned').textContent = candidates.length;
  document.getElementById('stat-shortlisted').textContent = rankedResults.length;
  document.getElementById('stat-topscore').textContent = rankedResults.length ? rankedResults[0].composite.toFixed(0) : '—';
  document.getElementById('stat-time').textContent = `${(pipelineTime / 1000).toFixed(2)}s`;

  currentResults = rankedResults;
  renderResults(sortResults(rankedResults));

  btn.disabled = false;
  btnText.textContent = '⚡ Find Best Candidates';

  setTimeout(() => {
    progressContainer.classList.remove('active');
  }, 1000);
}

function setStage(steps, index, state) {
  if (state === 'active') steps[index].classList.add('active');
  if (state === 'done') {
    steps[index].classList.remove('active');
    steps[index].classList.add('done');
  }
}

function sortResults(results) {
  const sorted = [...results];
  switch (currentSort) {
    case 'overall': sorted.sort((a, b) => b.composite - a.composite); break;
    case 'semantic': sorted.sort((a, b) => b.scores.semantic - a.scores.semantic); break;
    case 'receptivity': sorted.sort((a, b) => b.receptivity - a.receptivity); break;
    case 'trajectory': sorted.sort((a, b) => b.scores.career - a.scores.career); break;
  }
  return sorted;
}
