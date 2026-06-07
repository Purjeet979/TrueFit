import { AVATAR_COLORS, STOPWORDS } from './config.js';

export function clamp(val, min, max) {
  return Math.min(max, Math.max(min, val));
}

export function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

export function initials(name) {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

export function avatarColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

export function scoreColor(score) {
  if (score >= 80) return 'var(--green)';
  if (score >= 65) return 'var(--accent)';
  if (score >= 50) return 'var(--amber)';
  return 'var(--red)';
}

export function normalizeSkillName(name) {
  return name.toLowerCase().trim();
}

const STEM_PROTECT = new Set([
  'kubernetes', 'pandas', 'keras', 'jenkins', 'redis', 'postgres', 'aws', 'gans',
  'llms', 'transformers', 'series', 'analysis', 'models', 'systems', 'services',
  'queries', 'pipelines', 'architectures', 'databases', 'apis', 'microservices',
  'tables', 'modules', 'nodes', 'classes', 'interfaces', 'processes', 'instances',
  'metrics', 'features', 'candidates', 'engineers', 'years', 'skills',
  'languages', 'libraries', 'frameworks', 'tools', 'platforms', 'applications',
]);

export function stem(word) {
  let w = word.toLowerCase().trim();
  if (w.length <= 2) return w;
  if (STEM_PROTECT.has(w)) return w;
  if (w.endsWith('sses')) w = w.slice(0, -2);
  else if (w.endsWith('ies') && w.length > 4) w = w.slice(0, -3) + 'i';
  else if (w.endsWith('ss')) {}
  else if (w.endsWith('s') && !w.endsWith('us') && !w.endsWith('as') && !w.endsWith('is') && !w.endsWith('os')) w = w.slice(0, -1);
  
  if (w.endsWith('eed')) {
    if (w.length > 4) w = w.slice(0, -1);
  } else if (w.endsWith('ing')) {
    if (w.length > 5) {
      w = w.slice(0, -3);
      if (w.endsWith('at') || w.endsWith('bl') || w.endsWith('iz')) w += 'e';
    }
  } else if (w.endsWith('ed')) {
    if (w.length > 4) {
      w = w.slice(0, -2);
      if (w.endsWith('at') || w.endsWith('bl') || w.endsWith('iz')) w += 'e';
    }
  }
  return w;
}

export function tokenize(text) {
  return text.toLowerCase()
    .replace(/[^a-z0-9\s\-\.\/\+#]/g, ' ')
    .split(/\s+/)
    .filter(t => t.length > 1 && !STOPWORDS.has(t))
    .map(stem);
}

