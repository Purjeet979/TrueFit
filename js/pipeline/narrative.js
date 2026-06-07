import { normalizeSkillName } from '../utils.js';

export function generateNarrative(result, jdSignals, baselineDate = new Date()) {
  const { candidate, scores, composite, skillMatch: sm } = result;
  const p = candidate.profile;
  const sig = candidate.redrob_signals || {};

  // Strengths
  const strengths = [];

  if (scores.semantic >= 60) {
    strengths.push(`Strong semantic alignment with the job requirements — ${sm.matched}/${sm.total} key skills matched (${(sm.ratio * 100).toFixed(0)}% coverage). Profile vocabulary closely maps to the JD's technical domain.`);
  }

  if (scores.career >= 65) {
    const history = candidate.career_history || [];
    const avgTenure = history.length ? (history.reduce((s, h) => s + (h.duration_months || 0), 0) / history.length / 12).toFixed(1) : '—';
    strengths.push(`Solid career trajectory with ${history.length} role${history.length > 1 ? 's' : ''} averaging ${avgTenure} years tenure. Career arc shows ${scores.career >= 75 ? 'strong upward progression' : 'steady professional growth'} — a signal of stability and advancement.`);
  }

  if (scores.activity >= 60 && candidate.redrob_signals) {
    const parts = [];
    if (sig.open_to_work_flag) parts.push('actively open to work');
    if (sig.recruiter_response_rate >= 0.5) parts.push(`${(sig.recruiter_response_rate * 100).toFixed(0)}% recruiter response rate`);
    if (sig.profile_completeness_score >= 70) parts.push(`${sig.profile_completeness_score.toFixed(0)}% profile completeness`);
    if (parts.length) {
      strengths.push(`High receptivity signals: ${parts.join(', ')}. This candidate is ${sig.open_to_work_flag ? 'actively looking' : 'likely receptive'} and has strong engagement patterns.`);
    }
  }

  if (scores.skills >= 65) {
    const topSkills = (candidate.skills || [])
      .filter(s => s.proficiency === 'advanced' || s.proficiency === 'expert')
      .slice(0, 3)
      .map(s => s.name);
    if (topSkills.length) {
      strengths.push(`Deep skills in ${topSkills.join(', ')} at advanced/expert level, backed by ${p.years_of_experience.toFixed(1)} years of professional experience.`);
    }
  }

  if (scores.culture >= 65) {
    strengths.push(`Strong cultural alignment — background in ${p.current_industry} at a ${p.current_company_size} employee company maps well to the target environment and domain.`);
  }

  // Offer Acceptance Strength
  if (sig && sig.offer_acceptance_rate > 0.8) {
    strengths.push(`Highly reliable closer: Historical offer acceptance rate is ${(sig.offer_acceptance_rate * 100).toFixed(0)}%. Indicates strong intent when engaging with opportunities.`);
  }

  // Concerns
  const concerns = [];

  // Hard Block: required skill missing
  if (sm.unmatchedSkills.length > 0 && jdSignals.requiredSkills.length > 0) {
    const missingRequired = sm.unmatchedSkills.filter(s =>
      jdSignals.requiredSkills.some(rs => normalizeSkillName(rs) === normalizeSkillName(s))
    );
    if (missingRequired.length > 0) {
      concerns.push({
        tier: 'hard-block',
        tierLabel: 'Hard Block',
        text: `Missing required skill${missingRequired.length > 1 ? 's' : ''} from JD: ${missingRequired.join(', ')}. The job description explicitly marks ${missingRequired.length > 1 ? 'these as' : 'this as'} required — verify if the candidate has equivalent experience under a different name.`
      });
    }
  }

  // Flag: experience gap
  if (jdSignals.minExperience > 0 && p.years_of_experience < jdSignals.minExperience) {
    concerns.push({
      tier: 'flag',
      tierLabel: 'Flag',
      text: `Experience gap: ${p.years_of_experience.toFixed(1)} years vs ${jdSignals.minExperience}+ required. Probe: "Walk me through your most complex project — what was your scope of ownership and decision-making authority?"`,
    });
  }

  // Flag: leadership gap
  if (jdSignals.requiresLeadership) {
    const hasLeadership = (candidate.career_history || []).some(h =>
      /\b(led|managed|team of|mentor|lead)\b/i.test(h.description || '')
    );
    if (!hasLeadership) {
      concerns.push({
        tier: 'flag',
        tierLabel: 'Flag',
        text: `No explicit leadership experience detected, but role requires team leadership. Probe: "Have you ever been in a position where you had to guide or mentor others — formally or informally?"`,
      });
    }
  }

  // Watch: job hopping
  const history = candidate.career_history || [];
  const shortStints = history.filter(h => h.duration_months < 12).length;
  if (shortStints >= 2) {
    concerns.push({
      tier: 'watch',
      tierLabel: 'Watch',
      text: `${shortStints} roles under 12 months detected. Short tenure is increasingly common in the tech industry, especially in startup environments — context matters. Could indicate growth-seeking behavior rather than instability.`,
    });
  }

  // Watch: inactive profile
  if (candidate.redrob_signals && sig.last_active_date) {
    const daysSinceActive = Math.max(0, (baselineDate - new Date(sig.last_active_date)) / (1000 * 60 * 60 * 24));
    if (daysSinceActive > 90) {
      concerns.push({
        tier: 'watch',
        tierLabel: 'Watch',
        text: `Profile last active ${Math.floor(daysSinceActive)} days ago. Passive candidates can still be strong hires — they may not be actively looking but could be receptive to the right opportunity.`,
      });
    }
  }

  // Context: notice period
  if (sig && sig.notice_period_days > 60) {
    concerns.push({
      tier: 'context',
      tierLabel: 'Context',
      text: `Current notice period is ${sig.notice_period_days} days. This is standard for Indian enterprise companies and doesn't reflect candidate intent — early buyout negotiation is common for strong candidates.`,
    });
  }

  // Trust/Verification Warning
  let verifiedCount = 0;
  if (sig.verified_email) verifiedCount++;
  if (sig.verified_phone) verifiedCount++;
  if (sig.linkedin_connected) verifiedCount++;
  
  if (verifiedCount === 0) {
    concerns.push({
      tier: 'hard-block',
      tierLabel: 'Trust Warning',
      text: `Candidate lacks basic contact verification (no verified email, phone, or LinkedIn). High probability of spam/bot profile — proceed with extreme caution.`,
    });
  } else if (verifiedCount === 1) {
    concerns.push({
      tier: 'watch',
      tierLabel: 'Watch',
      text: `Candidate has limited contact verification. Ensure identity verification is completed early in the process.`,
    });
  }

  // Offer Acceptance Flag
  if (sig.offer_acceptance_rate >= 0) {
    if (sig.offer_acceptance_rate < 0.4) {
      concerns.push({
        tier: 'flag',
        tierLabel: 'Flag',
        text: `Candidate has a history of very low offer acceptance (${(sig.offer_acceptance_rate * 100).toFixed(0)}%). Probe heavily on their actual intent to leave their current role to avoid wasted cycles.`,
      });
    }
  }

  // Context: salary expectations
  if (sig && sig.expected_salary_range_inr_lpa) {
    const sal = sig.expected_salary_range_inr_lpa;
    concerns.push({
      tier: 'context',
      tierLabel: 'Context',
      text: `Expected salary range: ₹${sal.min.toFixed(1)}L — ₹${sal.max.toFixed(1)}L per annum. This provides a baseline for compensation planning and early alignment.`,
    });
  }

  // Probe Questions
  const probes = [];

  if (scores.semantic < 70) {
    probes.push(`Your background emphasizes ${p.current_industry}. How would you approach ramping up in ${jdSignals.domain !== 'general' ? jdSignals.domain : 'this domain'} — what's your learning framework for a new technical domain?`);
  }

  probes.push(`Tell me about a project where you owned the outcome end-to-end. What did you ship, what broke, and what would you do differently?`);

  if (jdSignals.requiresLeadership) {
    probes.push(`Describe a time you influenced a technical decision when you didn't have formal authority. How did you build consensus?`);
  }

  if (sm.matchedSkills.length > 0) {
    const focusSkill = sm.matchedSkills[0];
    probes.push(`You list ${focusSkill} on your profile. Walk me through the most challenging problem you solved using it — the constraints, your approach, and the outcome.`);
  }

  if (sig && sig.github_activity_score >= 0 && sig.github_activity_score < 30) {
    probes.push(`Your GitHub activity is relatively light. Do you contribute to open-source or personal projects outside work? What's your approach to continuous skill development?`);
  }

  // Outreach Draft
  const outreach = generateOutreach(candidate, jdSignals, composite);

  // Recruiter Summary
  const expStr = `${p.years_of_experience.toFixed(1)}y exp`;
  const roleLabels = {
    ml_engineer: 'machine learning engineer',
    data_engineer: 'data engineer',
    fullstack: 'full stack engineer',
    frontend: 'frontend engineer',
    backend: 'backend engineer',
    pm: 'product manager',
    operations: 'operations professional',
    marketing: 'marketing professional',
    business_analyst: 'business analyst',
    general_software: 'software engineer',
  };
  const familyLabel = roleLabels[jdSignals.roleFamily] || (jdSignals.roleFamily || 'general_software').replaceAll('_', ' ');
  const matchedString = sm.matchedSkills.slice(0, 3).join(', ') || 'key skills';
  const modeStr = sig.preferred_work_mode ? `prefers ${sig.preferred_work_mode} roles` : 'flexible work mode';
  const statusStr = sig.open_to_work_flag ? 'actively looking (Open to Work)' : 'a passive candidate';
  const recruiterSummary = `${p.anonymized_name} is a ${familyLabel} (${expStr}) currently at ${p.current_company || 'unlisted company'}. Demonstrates solid match with: ${matchedString}. Candidate is ${statusStr} and ${modeStr}.`;

  // Methodology Breakdown (whyChosen)
  const topScoreKeys = Object.keys(scores).sort((a, b) => scores[b] - scores[a]);
  const bestKey = topScoreKeys[0];
  const secondKey = topScoreKeys[1];
  
  const dimNames = {
      semantic: 'Semantic Fit',
      career: 'Career Trajectory',
      activity: 'Receptivity & Demand',
      skills: 'Skills Depth',
      culture: 'Cultural Alignment'
  };
  
  const githubStr = (sig && sig.github_activity_score >= 50) ? " coupled with strong verified engineering depth (high GitHub activity)" : "";
  const saveStr = (sig && sig.saved_by_recruiters_30d >= 5) ? " and high market demand (highly sought after by recruiters)" : "";
  const skillMatchStr = sm.matched > 0 ? ` driven by a solid match on core skills (${sm.matched}/${sm.total})` : "";
  
  const whyChosen = `Ranked with an overall score of ${composite.toFixed(0)} primarily due to exceptional ${dimNames[bestKey]} (${scores[bestKey].toFixed(0)}/100)${bestKey === 'semantic' || bestKey === 'skills' ? skillMatchStr : ''}. This is supported by a strong ${dimNames[secondKey]} (${scores[secondKey].toFixed(0)}/100)${saveStr}${githubStr}.`;

  return {
    strengths: strengths.slice(0, 3),
    concerns,
    probes: probes.slice(0, 4),
    outreach,
    receptivity: scores.activity,
    recruiterSummary,
    whyChosen,
  };
}

export function generateOutreach(candidate, jdSignals, score) {
  const p = candidate.profile;
  const firstName = p.anonymized_name.split(' ')[0];
  const domain = jdSignals.domain !== 'general' ? jdSignals.domain : 'technology';
  const seniorityPrefix = jdSignals.seniority === 'senior' ? 'Senior ' : jdSignals.seniority === 'junior' ? '' : '';

  return `Hi ${firstName},

I came across your profile and your background in ${p.current_industry} at ${p.current_company} caught my attention — particularly your ${p.years_of_experience.toFixed(0)}+ years of experience and expertise as a ${p.current_title}.

We're building something exciting in the ${domain} space and are looking for a ${seniorityPrefix}${p.current_title.toLowerCase().includes('engineer') ? 'engineer' : 'professional'} who brings exactly the kind of depth you've demonstrated.

Would you be open to a quick 15-minute chat this week? No commitment — just want to share what we're working on and see if there's mutual interest.

Best regards`;
}
