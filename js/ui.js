import { CONFIG, WEIGHT_LABELS, WEIGHT_COLORS, JD_PRESETS, SKILL_ALIASES } from './config.js';
import { initials, avatarColor, scoreColor, normalizeSkillName } from './utils.js';

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatRoleFamily(roleFamily) {
  const labels = {
    ml_engineer: 'ML ENGINEER',
    data_engineer: 'DATA ENGINEER',
    fullstack: 'FULL STACK',
    frontend: 'FRONTEND',
    backend: 'BACKEND',
    pm: 'PRODUCT MANAGER',
    operations: 'OPERATIONS',
    marketing: 'MARKETING',
    business_analyst: 'BUSINESS ANALYST',
    general_software: 'GENERAL SOFTWARE',
  };
  return labels[roleFamily] || String(roleFamily || 'general').replaceAll('_', ' ').toUpperCase();
}

export function renderPresets(onSelectPreset) {
  const grid = document.getElementById('preset-grid');
  grid.innerHTML = '';
  JD_PRESETS.forEach((p, i) => {
    const btn = document.createElement('button');
    btn.className = 'preset-btn';
    btn.textContent = p.label;
    btn.dataset.index = i;
    btn.id = `preset-btn-${i}`;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('jd-input').value = p.jd;
      if (onSelectPreset) onSelectPreset(p.jd);
    });
    grid.appendChild(btn);
  });
}

export function renderWeightSliders(weights) {
  const container = document.getElementById('weight-sliders');
  container.innerHTML = '';
  Object.entries(CONFIG.defaultWeights).forEach(([key, val]) => {
    const row = document.createElement('div');
    row.className = 'slider-row';
    row.innerHTML = `
      <span class="slider-name" style="color:${WEIGHT_COLORS[key]}">${WEIGHT_LABELS[key]}</span>
      <input type="range" class="slider-track" id="weight-${key}" min="0" max="100" value="${weights[key]}" data-key="${key}">
      <span class="slider-val" id="weight-val-${key}">${weights[key]}%</span>
    `;
    container.appendChild(row);
  });

  container.querySelectorAll('.slider-track').forEach(slider => {
    slider.addEventListener('input', e => {
      const key = e.target.dataset.key;
      weights[key] = parseInt(e.target.value);
      document.getElementById(`weight-val-${key}`).textContent = `${weights[key]}%`;
    });
  });
}

export function copyOutreach(btn, e) {
  e.stopPropagation();
  const text = btn.parentElement.querySelector('.outreach-text').textContent;
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = '✓ Copied';
    btn.classList.add('copied');
    setTimeout(() => {
      btn.textContent = 'Copy';
      btn.classList.remove('copied');
    }, 2000);
  });
}

export function createEmptyState(title, desc) {
  const div = document.createElement('div');
  div.className = 'empty-state';
  div.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M9.172 14.828a4 4 0 005.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
    <h3>${title}</h3>
    <p>${desc}</p>
  `;
  return div;
}

export function createCandidateCard(result, rank) {
  const { candidate, scores, composite, skillMatch: sm, narrative } = result;
  const p = candidate.profile;
  const sig = candidate.redrob_signals || {};

  const card = document.createElement('div');
  card.className = 'candidate-card';
  card.id = `candidate-${candidate.candidate_id}`;

  const rankClass = rank === 0 ? 'rank-1' : rank === 1 ? 'rank-2' : rank === 2 ? 'rank-3' : 'rank-n';
  const circumference = CONFIG.scoreRingCircumference;
  const offset = circumference - (composite / 100 * circumference);
  const ringColor = scoreColor(composite);

  const matchedSkillNames = sm.matchedSkills.map(s => normalizeSkillName(s));
  const candidateSkillNames = (candidate.skills || []).map(s => s.name);
  const matchedTags = candidateSkillNames.filter(s =>
    matchedSkillNames.some(ms => normalizeSkillName(s).includes(ms) || ms.includes(normalizeSkillName(s)))
    || sm.matchedSkills.some(ms => {
      const aliases = SKILL_ALIASES[normalizeSkillName(ms)] || [];
      return aliases.includes(normalizeSkillName(s));
    })
  );
  const unlistedTags = candidateSkillNames.filter(s => !matchedTags.includes(s));

  const matchedEvidence = sm.matches ? sm.matches.filter(m => m.source !== 'none') : [];
  const evidenceHTML = matchedEvidence.length ? `
    <div class="section-heading">Skill Match Evidence</div>
    <div class="evidence-grid" style="display:grid;grid-template-columns:repeat(auto-fill, minmax(170px, 1fr));gap:8px;margin-bottom:14px;">
      ${matchedEvidence.map(m => {
        let label = '';
        let color = '';
        if (m.source === 'explicit') { label = 'profile skill'; color = 'var(--green)'; }
        else if (m.source === 'history') { label = 'career timeline'; color = 'var(--blue)'; }
        else if (m.source === 'summary') { label = 'profile summary'; color = 'var(--amber)'; }
        else if (m.source === 'or_group') { label = 'alt group'; color = 'var(--teal)'; }
        else if (m.source === 'ontology') { label = 'equivalent'; color = 'var(--accent2)'; }
        return `
          <div style="padding:6px 10px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;font-size:12px;display:flex;flex-direction:column;gap:2px;">
            <div style="font-family:var(--font-mono);font-weight:500;color:var(--text);">${m.skill}</div>
            <div style="font-size:10px;color:${color};text-transform:uppercase;letter-spacing:0.5px;font-weight:600;">${label}</div>
          </div>
        `;
      }).join('')}
    </div>
  ` : '';

  card.innerHTML = `
    <!-- Layer 1: Identity + Score -->
    <div class="card-layer1">
      <div class="rank-badge ${rankClass}">#${rank + 1}</div>
      <div class="avatar" style="background:${avatarColor(p.anonymized_name)}">${initials(p.anonymized_name)}</div>
      <div class="card-info">
        <div class="card-name">${p.anonymized_name} <span class="fit-label ${result.fitLabel.toLowerCase()}">${result.fitLabel} Fit</span></div>
        <div class="card-title">${p.current_title} at ${p.current_company}</div>
        <div class="meta-chips">
          <span class="meta-chip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            ${p.location}
          </span>
          <span class="meta-chip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            ${p.years_of_experience.toFixed(1)}y exp
          </span>
          <span class="meta-chip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 3h-8l-2 4h12z"/></svg>
            ${sig.preferred_work_mode || 'flexible'}
          </span>
          ${sig.open_to_work_flag ? '<span class="meta-chip" style="color:var(--green);border:1px solid rgba(52,211,153,0.2);background:rgba(52,211,153,0.08)">✓ Open to work</span>' : ''}
          ${sig.saved_by_recruiters_30d >= 5 ? '<span class="meta-chip" style="color:var(--amber);border:1px solid rgba(251,191,36,0.2);background:rgba(251,191,36,0.08)">🔥 High Demand</span>' : ''}
          ${sig.skill_assessment_scores && Object.keys(sig.skill_assessment_scores).length > 0 ? '<span class="meta-chip" style="color:var(--accent2);border:1px solid rgba(165,148,255,0.2);background:rgba(165,148,255,0.08)">✓ Verified Skills</span>' : ''}
        </div>
        <div class="skill-tags">
          ${matchedTags.slice(0, 5).map(s => `<span class="skill-tag matched">${s}</span>`).join('')}
          ${unlistedTags.slice(0, 3).map(s => `<span class="skill-tag unlisted">${s}</span>`).join('')}
          ${candidateSkillNames.length > 8 ? `<span class="skill-tag unlisted">+${candidateSkillNames.length - 8}</span>` : ''}
        </div>
      </div>
      <div class="score-ring-wrap">
        <svg width="56" height="56" viewBox="0 0 56 56" aria-hidden="true">
          <circle class="track" cx="28" cy="28" r="${CONFIG.scoreRingRadius}"/>
          <circle class="fill" cx="28" cy="28" r="${CONFIG.scoreRingRadius}"
            stroke="${ringColor}"
            stroke-dasharray="${circumference}"
            stroke-dashoffset="${circumference}"
            data-target-offset="${offset}"/>
        </svg>
        <span class="score-ring-val" style="color:${ringColor}">${composite.toFixed(0)}</span>
      </div>
    </div>

    <!-- Layer 2: Signal Bars -->
    <div class="card-layer2">
      ${Object.entries(scores).map(([key, val]) => `
        <div class="signal-bar-item">
          <span class="signal-label">${WEIGHT_LABELS[key]}</span>
          <div class="signal-bar-track">
            <div class="signal-bar-fill" style="width:0%;background:${WEIGHT_COLORS[key]}" data-target-width="${val}%"></div>
          </div>
          <span class="signal-bar-val">${val.toFixed(0)}</span>
        </div>
      `).join('')}
    </div>

    <div class="expand-hint" id="hint-${candidate.candidate_id}">▼ click to expand full analysis</div>

    <!-- Layer 3: Expanded -->
    <div class="card-layer3">
      <div class="why-chosen-card" style="padding:16px;background:linear-gradient(135deg, rgba(124,109,250,0.12), rgba(124,109,250,0.02));border:1px solid rgba(124,109,250,0.3);border-radius:12px;margin-bottom:16px;font-size:13px;color:var(--text);line-height:1.6;box-shadow: 0 4px 12px rgba(0,0,0,0.2);">
        <div style="font-family:var(--font-mono);font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:8px;display:flex;align-items:center;gap:6px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
          Why This Candidate?
        </div>
        ${escapeHtml(narrative.whyChosen || '')}
      </div>

      <div class="recruiter-summary-card" style="padding:12px 16px;background:rgba(255,255,255,0.02);border:1px solid var(--border);border-radius:10px;margin-bottom:16px;font-size:13px;color:var(--text2);line-height:1.5;">
        <div style="font-family:var(--font-mono);font-size:10px;font-weight:600;color:var(--text3);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Recruiter's Executive Summary</div>
        ${escapeHtml(narrative.recruiterSummary || '')}
      </div>

      ${narrative.strengths.length ? `
        <div class="section-heading">Strengths</div>
        ${narrative.strengths.map(s => `<div class="strength-card">${s}</div>`).join('')}
      ` : ''}

      ${evidenceHTML}

      ${narrative.concerns.length ? `
        <div class="section-heading">Concerns</div>
        ${narrative.concerns.map(c => `
          <div class="concern-card ${c.tier}">
            <span class="concern-badge">${c.tierLabel}</span>
            <span>${c.text}</span>
          </div>
        `).join('')}
      ` : ''}

      <div class="section-heading">Receptivity</div>
      <div class="receptivity-bar">
        <div class="receptivity-header">
          <span class="receptivity-label">Likelihood to respond</span>
          <span class="receptivity-value">${narrative.receptivity.toFixed(0)}%</span>
        </div>
        <div class="receptivity-track">
          <div class="receptivity-fill" style="width:0%" data-target-width="${narrative.receptivity}%"></div>
        </div>
      </div>

      ${narrative.probes.length ? `
        <div class="section-heading">Screen Probe Questions</div>
        <ul class="probe-list">
          ${narrative.probes.map(q => `<li class="probe-item">${q}</li>`).join('')}
        </ul>
      ` : ''}

      <div class="section-heading">Outreach Draft</div>
      <div class="outreach-block">
        <button class="copy-btn">Copy</button>
        <div class="outreach-text">${narrative.outreach}</div>
      </div>

      <div class="expand-hint">▲ collapse</div>
    </div>
  `;

  // Copy button programmatic event listener
  const copyBtn = card.querySelector('.copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', (e) => {
      copyOutreach(copyBtn, e);
    });
  }

  // Click to expand/collapse
  card.addEventListener('click', (e) => {
    if (e.target.closest('.copy-btn') || e.target.closest('.outreach-text')) return;
    card.classList.toggle('expanded');
    const hint = document.getElementById(`hint-${candidate.candidate_id}`);
    if (hint) hint.textContent = card.classList.contains('expanded') ? '' : '▼ click to expand full analysis';

    // Animate fills on expand
    if (card.classList.contains('expanded')) {
      card.querySelectorAll('.receptivity-fill[data-target-width]').forEach(el => {
        setTimeout(() => { el.style.width = el.dataset.targetWidth; }, 100);
      });
    }
  });

  // Animate signal bars and score ring after render
  requestAnimationFrame(() => {
    setTimeout(() => {
      card.querySelectorAll('.signal-bar-fill[data-target-width]').forEach(el => {
        el.style.width = el.dataset.targetWidth;
      });
      card.querySelectorAll('.fill[data-target-offset]').forEach(el => {
        el.style.strokeDashoffset = el.dataset.targetOffset;
      });
    }, 100 + rank * 60);
  });

  return card;
}

export function renderResults(results) {
  const container = document.getElementById('candidate-list');
  const emptyState = document.getElementById('empty-state');

  if (!results.length) {
    container.innerHTML = '';
    container.appendChild(createEmptyState('No candidates match your filters', 'Try adjusting your hard filters or broadening the job description.'));
    return;
  }

  if (emptyState) emptyState.remove();
  container.innerHTML = '';

  results.forEach((result, i) => {
    const card = createCandidateCard(result, i);
    card.style.animationDelay = `${i * 60}ms`;
    container.appendChild(card);
  });
}

export function renderJDInsights(signals) {
  const card = document.getElementById('jd-insights-card');
  const content = document.getElementById('jd-insights-content');
  if (!card || !content) return;

  if (!signals) {
    card.style.display = 'none';
    return;
  }

  card.style.display = 'block';
  card.style.marginBottom = '16px'; // Space below card

  const { roleFamily, minExperience, constraints, orGroups, requiredSkills, preferredSkills } = signals;
  const { noticePeriodMax, workMode, workModeRequired, location, locationRequired, salaryMax } = constraints || {};

  // Formulating badges
  const roleLabel = formatRoleFamily(roleFamily);
  
  const modeBadge = workMode 
    ? `<span style="font-family:var(--font-mono);font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px;background:rgba(96,165,250,0.15);color:var(--blue);border:1px solid rgba(96,165,250,0.25);margin-left:4px;">
        ${escapeHtml(workMode.toUpperCase())} ${workModeRequired ? '(REQ)' : '(PREF)'}
       </span>`
    : 'Not Specified';

  const locBadge = location
    ? `<span style="font-family:var(--font-mono);font-size:11px;font-weight:600;padding:2px 6px;border-radius:4px;background:rgba(45,212,191,0.15);color:var(--teal);border:1px solid rgba(45,212,191,0.25);margin-left:4px;">
        ${escapeHtml(location)} ${locationRequired ? '(REQ)' : '(PREF)'}
       </span>`
    : 'Not Specified';

  const salaryBadge = salaryMax ? `₹${salaryMax} LPA max` : 'Not Specified';
  const noticeBadge = noticePeriodMax ? `${noticePeriodMax} days max` : 'Flexible';

  // OR group string
  const orGroupsStr = orGroups && orGroups.length > 0
    ? orGroups.map(group => `<code>${group.map(escapeHtml).join(' or ')}</code>`).join(', ')
    : 'None detected';
  const requiredSkillsStr = requiredSkills?.length ? requiredSkills.map(escapeHtml).join(', ') : 'None';
  const preferredSkillsStr = preferredSkills?.length ? preferredSkills.map(escapeHtml).join(', ') : '';

  content.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:8px;">
      <div style="font-size:12px;color:var(--text3);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:0.5px;">Role & Experience</div>
      <div style="font-size:13px;color:var(--text);font-weight:600;display:flex;align-items:center;flex-wrap:wrap;gap:6px;">
        <span style="font-family:var(--font-mono);font-size:11px;background:rgba(124,109,250,0.15);color:var(--accent2);padding:2px 6px;border-radius:4px;border:1px solid rgba(124,109,250,0.25);">${escapeHtml(roleLabel)}</span>
        <span>${minExperience}+ years exp</span>
      </div>
    </div>
    
    <div style="display:flex;flex-direction:column;gap:8px;">
      <div style="font-size:12px;color:var(--text3);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:0.5px;">Work Mode & Location</div>
      <div style="font-size:13px;color:var(--text);display:flex;flex-wrap:wrap;gap:4px;align-items:center;">
        ${modeBadge} ${workMode && location ? '·' : ''} ${location ? locBadge : ''}
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px;">
      <div style="font-size:12px;color:var(--text3);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:0.5px;">Budget & Notice Period</div>
      <div style="font-size:13px;color:var(--text);font-family:var(--font-mono);">
        <span style="color:var(--amber);font-weight:500;">${salaryBadge}</span> · <span>${noticeBadge} notice</span>
      </div>
    </div>

    <div style="display:flex;flex-direction:column;gap:8px;grid-column:1 / -1;border-top:1px solid var(--border);padding-top:12px;">
      <div style="font-size:12px;color:var(--text3);font-family:var(--font-mono);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Core Skill Requirements & OR Alternatives</div>
      <div style="font-size:13px;color:var(--text);line-height:1.5;">
        <strong style="color:var(--green);">Required:</strong> ${requiredSkillsStr}<br>
        ${preferredSkillsStr ? `<strong style="color:var(--accent2);">Preferred:</strong> ${preferredSkillsStr}<br>` : ''}
        <strong style="color:var(--blue);">Alternatives (OR Groups):</strong> ${orGroupsStr}
      </div>
    </div>
  `;
}
