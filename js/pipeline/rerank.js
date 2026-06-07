import { SKILL_ALIASES, SKILL_ONTOLOGY } from '../config.js';
import { normalizeSkillName, clamp } from '../utils.js';

function aliasesForSkill(skill) {
  const norm = normalizeSkillName(skill || '');
  const aliases = new Set([norm]);

  if (SKILL_ALIASES[norm]) {
    SKILL_ALIASES[norm].forEach(alias => aliases.add(normalizeSkillName(alias)));
  }

  Object.entries(SKILL_ALIASES).forEach(([key, values]) => {
    const normalizedValues = values.map(normalizeSkillName);
    if (normalizeSkillName(key) === norm || normalizedValues.includes(norm)) {
      aliases.add(normalizeSkillName(key));
      normalizedValues.forEach(alias => aliases.add(alias));
    }
  });

  return aliases;
}

function candidateSkillIndex(candidateSkills) {
  const index = new Map();
  candidateSkills.forEach(skill => {
    aliasesForSkill(skill.name).forEach(alias => index.set(alias, skill));
  });
  return index;
}

function candidateEvidenceText(candidate) {
  return [
    candidate.profile?.headline || '',
    candidate.profile?.summary || '',
    candidate.profile?.current_title || '',
    candidate.profile?.current_industry || '',
    ...(candidate.career_history || []).map(h => `${h.title || ''} ${h.industry || ''} ${h.description || ''}`),
    ...(candidate.education || []).map(e => `${e.degree || ''} ${e.field_of_study || ''}`),
  ].join(' ').toLowerCase();
}

function textHasSkill(text, skill) {
  return [...aliasesForSkill(skill)].some(alias => {
    if (!alias) return false;
    const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const startBoundary = /^[a-z0-9]/i.test(alias) ? '(?:^|[^a-z0-9._\\+#-])' : '(?:^|\\s)';
    const endBoundary = /[a-z0-9]$/i.test(alias) ? '(?=$|[^a-z0-9._\\+#-])' : '(?=$|\\s|[^a-z0-9_\\+#])';
    return new RegExp(startBoundary + escaped + endBoundary, 'i').test(text);
  });
}

function ontologyGroupForSkill(skill) {
  const norm = normalizeSkillName(skill);
  const groupEntry = Object.entries(SKILL_ONTOLOGY).find(([group, skills]) =>
    skills.map(normalizeSkillName).includes(norm)
  );
  return groupEntry ? groupEntry[0] : null;
}

function findOntologyMatch(candidateSkills, targetSkill) {
  const targetGroup = ontologyGroupForSkill(targetSkill);
  if (!targetGroup) return null;
  
  const matchedSkill = candidateSkills.find(s => {
    const group = ontologyGroupForSkill(s.name);
    return group === targetGroup;
  });
  
  return matchedSkill ? matchedSkill.name : null;
}

export function skillMatch(candidateSkills, jdSkills) {
  const candidateAliased = candidateSkillIndex(candidateSkills);

  let matched = 0;
  const matchedSkills = [];
  const unmatchedSkills = [];

  jdSkills.forEach(jdSkill => {
    const isMatched = [...aliasesForSkill(jdSkill)].some(alias => candidateAliased.has(alias));
    if (isMatched) {
      matched++;
      matchedSkills.push(jdSkill);
    } else {
      unmatchedSkills.push(jdSkill);
    }
  });

  return {
    ratio: jdSkills.length > 0 ? matched / jdSkills.length : 0,
    matched,
    total: jdSkills.length,
    matchedSkills,
    unmatchedSkills,
  };
}

export function detailedCandidateSkillMatch(candidate, jdSignals) {
  const candidateAliased = candidateSkillIndex(candidate.skills || []);
  const textHistory = (candidate.career_history || []).map(h => `${h.title || ''} ${h.industry || ''} ${h.description || ''}`).join(' ').toLowerCase();
  const textSummary = [candidate.profile?.headline || '', candidate.profile?.summary || ''].join(' ').toLowerCase();
  
  const required = jdSignals.requiredSkills || [];
  const preferred = jdSignals.preferredSkills || [];
  const fallback = required.length || preferred.length ? [] : (jdSignals.allSkills || []);
  
  const weightedSkills = [
    ...required.map(skill => ({ skill, weight: 2.0, isRequired: true })),
    ...preferred.map(skill => ({ skill, weight: 1.0, isRequired: false })),
    ...fallback.map(skill => ({ skill, weight: 1.25, isRequired: false })),
  ];

  let matchedWeight = 0;
  let totalWeight = 0;
  const matches = []; // { skill, source, credit, details }
  const requiredMissing = [];

  weightedSkills.forEach(({ skill, weight, isRequired }) => {
    totalWeight += weight;
    
    // Check for "OR" groups first
    const orGroup = (jdSignals.orGroups || []).find(group =>
      group.map(normalizeSkillName).includes(normalizeSkillName(skill))
    );
    if (orGroup) {
      const otherSkills = orGroup.filter(s => normalizeSkillName(s) !== normalizeSkillName(skill));
      const otherMatched = otherSkills.some(otherSkill => {
        const explicitMatch = [...aliasesForSkill(otherSkill)].some(alias => candidateAliased.has(alias));
        const textMatch = explicitMatch || textHasSkill(textHistory, otherSkill) || textHasSkill(textSummary, otherSkill);
        return textMatch;
      });
      
      if (otherMatched) {
        matches.push({
          skill,
          source: 'or_group',
          credit: weight,
          details: `Alternative skill matched in group`
        });
        matchedWeight += weight;
        return;
      }
    }

    // 1. Explicit skill match (alias-aware)
    const explicitAlias = [...aliasesForSkill(skill)].find(alias => candidateAliased.has(alias));
    if (explicitAlias) {
      const matchedSkillObj = candidateAliased.get(explicitAlias);
      matches.push({
        skill,
        source: 'explicit',
        credit: weight,
        details: `Matched from skill profile ("${matchedSkillObj.name}")`
      });
      matchedWeight += weight;
      return;
    }
    
    // 2. Career history evidence match
    if (textHasSkill(textHistory, skill)) {
      matches.push({
        skill,
        source: 'history',
        credit: weight * 0.75,
        details: `Evidence found in career timeline`
      });
      matchedWeight += weight * 0.75;
      return;
    }
    
    // 3. Profile summary evidence match
    if (textHasSkill(textSummary, skill)) {
      matches.push({
        skill,
        source: 'summary',
        credit: weight * 0.5,
        details: `Mentioned in profile summary/headline`
      });
      matchedWeight += weight * 0.5;
      return;
    }
    
    // 4. Ontology equivalent skill match
    const ontologyMatchName = findOntologyMatch(candidate.skills || [], skill);
    if (ontologyMatchName) {
      matches.push({
        skill,
        source: 'ontology',
        credit: weight * 0.4,
        details: `Equivalent skill found: "${ontologyMatchName}"`
      });
      matchedWeight += weight * 0.4;
      return;
    }
    
    // 5. No match
    matches.push({
      skill,
      source: 'none',
      credit: 0,
      details: `Missing`
    });
    if (isRequired) {
      requiredMissing.push(skill);
    }
  });

  return {
    ratio: totalWeight > 0 ? matchedWeight / totalWeight : 0,
    matches,
    requiredMissing
  };
}

export function weightedCandidateSkillMatch(candidate, jdSignals) {
  const res = detailedCandidateSkillMatch(candidate, jdSignals);
  const matchedMatches = res.matches.filter(m => m.source !== 'none');
  const unmatchedMatches = res.matches.filter(m => m.source === 'none');
  return {
    ratio: res.ratio,
    matched: matchedMatches.length,
    total: res.matches.length,
    matchedSkills: matchedMatches.map(m => m.skill),
    unmatchedSkills: unmatchedMatches.map(m => m.skill),
    requiredMissing: res.requiredMissing,
    matches: res.matches,
  };
}

export function semanticScore(similarity, candidate, jdSignals) {
  // Cosine similarities with TF-IDF are typically in 0.0 - 0.3 range
  // Scale so that 0.0 = 10, 0.05 = 30, 0.10 = 50, 0.20 = 75, 0.30+ = 90+
  const scaledSim = Math.min(similarity / 0.25, 1.0);
  const base = scaledSim * 80 + 10;
  
  const sm = detailedCandidateSkillMatch(candidate, jdSignals);
  const skillBoost = Math.min(sm.ratio * 15, 15);
  
  return Math.min(100, base + skillBoost);
}


export function careerTrajectoryScore(candidate) {
  const history = candidate.career_history || [];
  if (history.length === 0) return 30;

  // Promotion detection - check for actual upward title movement
  const seniorityKeywords = ['intern', 'junior', 'associate', 'analyst', 'engineer', 'developer',
    'senior', 'lead', 'staff', 'principal', 'manager', 'director', 'vp', 'head', 'cto', 'ceo'];
  function titleLevel(title) {
    const t = title.toLowerCase();
    for (let i = seniorityKeywords.length - 1; i >= 0; i--) {
      if (t.includes(seniorityKeywords[i])) return i;
    }
    return 5;
  }

  let promotions = 0;
  const totalYears = candidate.profile.years_of_experience || 1;
  for (let i = 1; i < history.length; i++) {
    // history[0] is current/most recent, history[N] is oldest
    const olderLevel = titleLevel(history[i].title || '');
    const newerLevel = titleLevel(history[i-1].title || '');
    if (newerLevel > olderLevel) promotions++;
  }
  const promotionRate = Math.min(promotions / Math.max(totalYears / 3, 1), 1) * 100;

  const avgTenure = history.reduce((s, h) => s + (h.duration_months || 0), 0) / history.length;
  let tenureScore;
  if (avgTenure >= 24) tenureScore = 80 + Math.min((avgTenure - 24) / 24, 1) * 20;
  else if (avgTenure >= 12) tenureScore = 50 + (avgTenure - 12) / 12 * 30;
  else tenureScore = avgTenure / 12 * 50;

  const first = titleLevel(history[history.length - 1].title || '');
  const last = titleLevel(history[0].title || '');
  let arcScore = 50;
  if (last > first) arcScore = 70 + Math.min((last - first) * 5, 30);
  else if (last === first && history.length > 1) arcScore = 55;
  else if (last < first) arcScore = 30;

  let leadershipBonus = 0;
  history.forEach(h => {
    const desc = (h.description || '').toLowerCase();
    if (/\b(led|managed|team of|mentored|oversaw)\b/.test(desc)) leadershipBonus = 10;
  });

  return clamp(promotionRate * 0.4 + tenureScore * 0.3 + arcScore * 0.3 + leadershipBonus, 0, 100);
}

export function activityScore(candidate, baselineDate = new Date()) {
  const sig = candidate.redrob_signals;
  if (!sig) return 30;

  const lastActive = new Date(sig.last_active_date);
  if (Number.isNaN(lastActive.getTime())) return 30;
  const daysSinceActive = Math.max(0, (baselineDate - lastActive) / (1000 * 60 * 60 * 24));
  let recencyScore;
  if (daysSinceActive <= 7) recencyScore = 100;
  else if (daysSinceActive <= 30) recencyScore = 80;
  else if (daysSinceActive <= 90) recencyScore = 60;
  else if (daysSinceActive <= 180) recencyScore = 40;
  else recencyScore = 20;

  const otwScore = sig.open_to_work_flag ? 100 : 20;
  const profileScore = sig.profile_completeness_score || 0;
  const responseScore = (sig.recruiter_response_rate || 0) * 100;

  // Market Demand & Reliability (Logarithmic scaling for heavy-tail data)
  // Max searches in dataset is 1490. log10(1490) is ~3.17.
  const searchAppearance = Math.min(Math.log10(1 + (sig.search_appearance_30d || 0)) / 3.17, 1) * 100;
  // Max saves in dataset is 80. log10(80) is ~1.9.
  const saves = Math.min(Math.log10(1 + (sig.saved_by_recruiters_30d || 0)) / 1.9, 1) * 100;
  const interviewCompletion = (sig.interview_completion_rate >= 0 ? sig.interview_completion_rate : 0.5) * 100;

  let baseActivity = recencyScore * 0.15 + otwScore * 0.15 + profileScore * 0.10 + responseScore * 0.10 + searchAppearance * 0.10 + saves * 0.20 + interviewCompletion * 0.20;

  // Trust & Verification Penalty
  let verifiedCount = 0;
  if (sig.verified_email) verifiedCount++;
  if (sig.verified_phone) verifiedCount++;
  if (sig.linkedin_connected) verifiedCount++;
  
  if (verifiedCount === 0) baseActivity -= 40; // High probability of bot/spam
  else if (verifiedCount === 1) baseActivity -= 15;
  else if (verifiedCount === 3) baseActivity += 5; // Small boost for fully verified

  // Offer Acceptance Rate Impact
  if (sig.offer_acceptance_rate >= 0) { // Not -1
    if (sig.offer_acceptance_rate < 0.4) baseActivity -= 25; // Flaky candidate
    else if (sig.offer_acceptance_rate > 0.8) baseActivity += 15; // Reliable closer
  }

  return clamp(baseActivity, 0, 100);
}

export function skillsDepthScore(candidate, jdSignals) {
  const candSkills = candidate.skills || [];
  const sm = detailedCandidateSkillMatch(candidate, jdSignals);

  const matchScore = jdSignals.allSkills.length > 0 ? sm.ratio * 100 : 80;

  const yearsExp = candidate.profile.years_of_experience || 0;
  const minReq = jdSignals.minExperience || 0;
  let expFit;
  if (yearsExp >= minReq) {
    expFit = Math.min(80 + (yearsExp - minReq) * 2, 100);
  } else {
    expFit = Math.max(0, 60 - (minReq - yearsExp) * 10);
  }

  const edu = candidate.education || [];
  let eduScore = 40;
  edu.forEach(e => {
    if (e.tier === 'tier_1') eduScore = Math.max(eduScore, 95);
    else if (e.tier === 'tier_2') eduScore = Math.max(eduScore, 75);
    else if (e.tier === 'tier_3') eduScore = Math.max(eduScore, 55);
    else eduScore = Math.max(eduScore, 40);
    if (/ph\.?d|doctorate/i.test(e.degree)) eduScore = Math.min(eduScore + 10, 100);
    else if (/m\.?s|m\.?tech|m\.?e|mba/i.test(e.degree)) eduScore = Math.min(eduScore + 5, 100);
  });

  let recencyBonus = 0;
  candSkills.forEach(s => {
    if (s.duration_months && s.duration_months <= 12) {
      if (jdSignals.allSkills.some(js => aliasesForSkill(js).has(normalizeSkillName(s.name)))) {
        recencyBonus += 3;
      }
    }
  });
  recencyBonus = Math.min(recencyBonus, 10);

  const proficiencyWeight = { beginner: 45, intermediate: 70, advanced: 90, expert: 100 };
  const matchingSkills = candSkills.filter(s =>
    sm.matches.some(m => m.source !== 'none' && aliasesForSkill(m.skill).has(normalizeSkillName(s.name)))
  );
  const proficiencyScore = matchingSkills.length
    ? matchingSkills.reduce((sum, s) => sum + (proficiencyWeight[s.proficiency] || 60), 0) / matchingSkills.length
    : 45;

  const assessmentScores = candidate.redrob_signals?.skill_assessment_scores || {};
  const relevantAssessments = Object.entries(assessmentScores)
    .filter(([skill]) => jdSignals.allSkills.some(js => aliasesForSkill(js).has(normalizeSkillName(skill))))
    .map(([, score]) => score);
  
  let assessmentScore = proficiencyScore;
  let useAssessment = false;
  if (relevantAssessments.length > 0) {
    assessmentScore = relevantAssessments.reduce((sum, score) => sum + score, 0) / relevantAssessments.length;
    useAssessment = true;
  }

  const githubScore = candidate.redrob_signals?.github_activity_score || -1;
  let githubBonus = 0;
  if (['ml_engineer', 'data_engineer', 'frontend', 'backend', 'fullstack', 'general_software'].includes(jdSignals.roleFamily)) {
    if (githubScore >= 50) githubBonus = 15;
    else if (githubScore >= 20) githubBonus = 10;
    else if (githubScore > 0) githubBonus = 5;
  }

  let finalScore;
  if (useAssessment) {
    finalScore = matchScore * 0.40 + expFit * 0.15 + eduScore * 0.15 + assessmentScore * 0.30 + recencyBonus + githubBonus;
  } else {
    finalScore = matchScore * 0.48 + expFit * 0.18 + eduScore * 0.16 + proficiencyScore * 0.18 + recencyBonus + githubBonus;
  }

  return clamp(finalScore, 0, 100);
}

export function culturalAlignmentScore(candidate, jdSignals) {
  const compSize = candidate.profile.current_company_size || '';
  let stageFit = 50;
  if (jdSignals.domain === 'fintech' || jdSignals.domain === 'saas') {
    if (['1-10','11-50','51-200','201-500'].includes(compSize)) stageFit = 85;
    else if (['501-1000','1001-5000'].includes(compSize)) stageFit = 65;
    else stageFit = 45;
  } else {
    if (['5001-10000','10001+'].includes(compSize)) stageFit = 80;
    else if (['1001-5000'].includes(compSize)) stageFit = 70;
    else stageFit = 50;
  }

  const history = candidate.career_history || [];
  const industries = history.map(h => (h.industry || '').toLowerCase());
  const currentIndustry = (candidate.profile.current_industry || '').toLowerCase();
  let domainConsistency = 40;
  const uniqueIndustries = new Set(industries);
  if (uniqueIndustries.size <= 2) domainConsistency = 80;
  else if (uniqueIndustries.size <= 3) domainConsistency = 60;

  let domainMatch = 40;
  const domainKeywords = {
    fintech: ['fintech', 'financial', 'banking', 'insurance'],
    healthcare: ['health', 'medical', 'pharma'],
    ecommerce: ['ecommerce', 'retail', 'marketplace'],
    saas: ['saas', 'software', 'it services', 'technology'],
    ai: ['ai', 'artificial intelligence', 'machine learning', 'data'],
  };
  if (jdSignals.domain !== 'general' && domainKeywords[jdSignals.domain]) {
    const keywords = domainKeywords[jdSignals.domain];
    if (keywords.some(k => currentIndustry.includes(k))) domainMatch = 90;
    else if (industries.some(ind => keywords.some(k => ind.includes(k)))) domainMatch = 70;
  }

  return clamp(stageFit * 0.4 + domainConsistency * 0.3 + domainMatch * 0.3, 0, 100);
}

export function seniorityFitScore(candidate, jdSignals) {
  const years = candidate.profile?.years_of_experience || 0;
  const title = `${candidate.profile?.current_title || ''} ${candidate.profile?.headline || ''}`.toLowerCase();
  const historyText = (candidate.career_history || []).map(h => h.description || '').join(' ').toLowerCase();

  let scopeBoost = 0;
  if (/team of \d+|managed \d+|led \d+/.test(historyText)) scopeBoost += 10;
  if (/architecture|system design|scaling|infrastructure/.test(historyText)) scopeBoost += 10;
  if (/\d+%\s*(?:increase|growth|improvement|reduction)|\$\d+/.test(historyText)) scopeBoost += 10;

  if (jdSignals.seniority === 'senior') {
    const titleFit = /\b(senior|sr\.?|lead|staff|principal|architect|manager|head|director)\b/.test(title) ? 100 : 65;
    const expFit = years >= Math.max(jdSignals.minExperience || 0, 5) ? 100 : Math.max(35, years * 14);
    return clamp(titleFit * 0.4 + expFit * 0.5 + scopeBoost, 0, 100);
  }

  if (jdSignals.seniority === 'junior') {
    if (years <= 3) return 95;
    if (years <= 5) return 75;
    return 45;
  }

  if (years < Math.max(jdSignals.minExperience || 0, 1)) return 55;
  return clamp(70 + Math.min(years, 8) * 3 + scopeBoost, 70, 100);
}

export function leadershipFitScore(candidate, jdSignals) {
  if (!jdSignals.requiresLeadership) return 80;
  const leadershipText = [
    candidate.profile?.headline || '',
    candidate.profile?.summary || '',
    ...(candidate.career_history || []).map(h => `${h.title || ''} ${h.description || ''}`),
  ].join(' ');

  if (/\b(led|lead|managed|manager|mentored|mentor|team of|oversaw|owned|stakeholder)\b/i.test(leadershipText)) {
    return 95;
  }
  return 45;
}

export function multiSignalReRank(filtered, similarities, signals, weights, globalCandidates) {
  const simMap = {};
  similarities.forEach(s => { simMap[s.index] = s.similarity; });

  let baselineDate = new Date("2026-01-01");
  let maxActiveTime = 0;
  globalCandidates.forEach(c => {
    if (c.redrob_signals && c.redrob_signals.last_active_date) {
      const d = new Date(c.redrob_signals.last_active_date).getTime();
      if (d > maxActiveTime) maxActiveTime = d;
    }
  });
  if (maxActiveTime > 0) {
    baselineDate = new Date(maxActiveTime);
  }

  // 1. Strict Hard Filtering Phase
  const passedCandidates = filtered.filter(candidate => {
    // A. Experience Constraint
    const minExp = signals.minExperience || 0;
    if (candidate.profile.years_of_experience < minExp) return false;

    // B. Required Skill Coverage Constraint (min 25% match)
    const required = signals.requiredSkills || [];
    if (required.length > 0) {
      const sm = weightedCandidateSkillMatch(candidate, signals);
      const matchedRequired = required.filter(skill => {
        const m = sm.matches.find(match => normalizeSkillName(match.skill) === normalizeSkillName(skill));
        return m && m.source !== 'none';
      }).length;
      if ((matchedRequired / required.length) < 0.25) return false;
    }

    // C. Work Mode Constraint
    if (signals.constraints?.workMode && signals.constraints.workModeRequired) {
      const candMode = candidate.redrob_signals?.preferred_work_mode;
      if (candMode && candMode !== signals.constraints.workMode && candMode !== 'flexible') return false;
    }

    // D. Location Constraint
    if (signals.constraints?.location && signals.constraints.locationRequired) {
      const candLoc = candidate.profile.location || '';
      if (!candLoc.toLowerCase().includes(signals.constraints.location.toLowerCase())) return false;
    }

    return true;
  });

  // Fallback to all filtered if hard filters exclude everyone
  const poolToRank = passedCandidates.length > 0 ? passedCandidates : filtered;

  const results = poolToRank.map(candidate => {
    const idx = globalCandidates.indexOf(candidate);
    const sim = simMap[idx] || 0;

    const scores = {
      semantic: semanticScore(sim, candidate, signals),
      career: careerTrajectoryScore(candidate),
      activity: activityScore(candidate, baselineDate),
      skills: skillsDepthScore(candidate, signals),
      culture: culturalAlignmentScore(candidate, signals),
    };

    const totalWeight = Object.values(weights).reduce((a, b) => a + b, 0) || 1;
    
    // Required missing penalty
    const sm = weightedCandidateSkillMatch(candidate, signals);
    const requiredCoverage = signals.requiredSkills?.length
      ? 1 - (sm.requiredMissing.length / signals.requiredSkills.length)
      : 1;
    const requiredPenalty = requiredCoverage < 0.5 ? 18 : requiredCoverage < 0.8 ? 8 : 0;
    
    // Seniority & Leadership fit
    const seniorityFit = seniorityFitScore(candidate, signals);
    const leadershipFit = leadershipFitScore(candidate, signals);
    const roleFit = (seniorityFit * 0.6 + leadershipFit * 0.4 - 80) * 0.12;

    const rawComposite = clamp(
      (scores.semantic * weights.semantic +
       scores.career * weights.career +
       scores.activity * weights.activity +
       scores.skills * weights.skills +
       scores.culture * weights.culture) / totalWeight + roleFit - requiredPenalty,
      0, 100
    );

    return {
      candidate,
      scores,
      rawComposite,
      similarity: sim,
      skillMatch: sm,
      receptivity: activityScore(candidate, baselineDate),
    };
  });

  // 2. Score Calibration Phase
  if (results.length > 0) {
    results.forEach(r => {
      // Keep absolute quality meaningful while avoiding overly compressed low scores.
      const calibrated = clamp(r.rawComposite * 1.12 + 6, 0, 100);
      r.composite = calibrated;

      // Assign labels
      if (calibrated >= 85) r.fitLabel = 'Excellent';
      else if (calibrated >= 70) r.fitLabel = 'Strong';
      else if (calibrated >= 45) r.fitLabel = 'Possible';
      else r.fitLabel = 'Weak';
    });
  }

  results.sort((a, b) => b.composite - a.composite);
  return results.slice(0, 20); // CONFIG.topK is 20
}
