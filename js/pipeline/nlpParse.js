import { SKILL_ALIASES } from '../config.js';
import { normalizeSkillName } from '../utils.js';

function makeSkillRegex(pattern) {
  const escaped = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const { startBoundary, endBoundary } = skillBoundaries(pattern);
  return new RegExp(startBoundary + escaped + endBoundary, 'i');
}

function skillBoundaries(pattern) {
  return {
    startBoundary: /^[a-zA-Z0-9]/.test(pattern) ? '(?:^|[^a-zA-Z0-9._\\+#-])' : '(?:^|\\s)',
    endBoundary: /[a-zA-Z0-9]$/.test(pattern) ? '(?=$|[^a-zA-Z0-9._\\+#-])' : '(?=$|\\s|[^a-zA-Z0-9_\\+#])',
  };
}

function addUnique(list, value) {
  if (!list.some(item => normalizeSkillName(item) === normalizeSkillName(value))) {
    list.push(value);
  }
}

function canonicalSkill(pattern) {
  const norm = normalizeSkillName(pattern);
  const direct = Object.keys(SKILL_ALIASES).find(skill => normalizeSkillName(skill) === norm);
  if (direct) return direct;

  const aliasOwner = Object.entries(SKILL_ALIASES).find(([, aliases]) =>
    aliases.some(alias => normalizeSkillName(alias) === norm)
  );
  return aliasOwner ? aliasOwner[0] : pattern;
}

function addOrGroup(groups, skills) {
  const uniqueSkills = [];
  skills.forEach(skill => addUnique(uniqueSkills, skill));
  if (uniqueSkills.length < 2) return;

  const normalized = uniqueSkills.map(normalizeSkillName).sort();
  const exists = groups.some(group => {
    const groupNormalized = group.map(normalizeSkillName).sort();
    return groupNormalized.length === normalized.length &&
      groupNormalized.every((skill, index) => skill === normalized[index]);
  });
  if (!exists) groups.push(uniqueSkills);
}

export function nlpParse(jdText) {
  const signals = {
    requiredSkills: [],
    preferredSkills: [],
    seniority: 'mid',
    requiresLeadership: false,
    domain: 'general',
    minExperience: 0,
    allSkills: [],
    titleKeywords: [],
    orGroups: [],
  };

  // Seniority detection
  if (/\b(senior|sr\.?|lead|principal|staff|architect)\b/i.test(jdText)) signals.seniority = 'senior';
  else if (/\b(junior|jr\.?|entry[- ]level|intern|fresher)\b/i.test(jdText)) signals.seniority = 'junior';

  // Leadership detection
  if (/\b(lead\s+a?\s*team|manage\s+engineers?|mentor|leadership|team\s+lead|tech\s+lead|engineering\s+manager)\b/i.test(jdText)) {
    signals.requiresLeadership = true;
  }

  // Domain detection
  const domains = {
    fintech: /\b(fintech|financial|banking|payment|credit|fraud|lending)\b/i,
    healthcare: /\b(health|medical|pharma|clinical|biotech)\b/i,
    ecommerce: /\b(e-?commerce|retail|marketplace|shopping)\b/i,
    saas: /\b(saas|b2b|enterprise\s+software|platform)\b/i,
    ai: /\b(artificial\s+intelligence|machine\s+learning|deep\s+learning|ai|ml)\b/i,
  };
  for (const [domain, regex] of Object.entries(domains)) {
    if (regex.test(jdText)) { signals.domain = domain; break; }
  }

  // Experience extraction
  const expMatches = [...jdText.matchAll(/(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)?/gi)];
  if (expMatches.length) {
    signals.minExperience = Math.min(...expMatches.map(match => parseFloat(match[1])));
  }

  // Skill extraction (required vs preferred)
  const sections = jdText
    .replace(/\b(required skills?|requirements?|preferred|nice[\s-]to[\s-]have|good[\s-]to[\s-]have)\s*:/gi, '\n$&')
    .split(/\n|;/);
  let currentSection = 'general';

  const skillPatterns = [
    'python','javascript','js','typescript','react','react.js','angular','vue','node.js','nodejs',
    'java','c++','c#','go','golang','rust','ruby','php','swift','kotlin',
    'sql','postgresql','postgres','mysql','mongodb','mongo','redis','elasticsearch',
    'aws','amazon web services','gcp','google cloud','azure','docker','kubernetes','k8s','terraform',
    'pytorch','tensorflow','scikit-learn','keras','pandas','numpy',
    'spark','pyspark','airflow','kafka','hadoop','databricks','snowflake',
    'nlp','natural language processing','deep learning','machine learning','computer vision','llm','llms',
    'large language models','fine-tuning','fine tuning','transformers','bert','gpt','rag','langchain','llamaindex',
    'vector db','vector database','chromadb','weaviate','pinecone','milvus',
    'next.js','nextjs','svelte','tailwind','tailwindcss','material ui','mui',
    'fastapi','django','flask','express','nestjs','spring boot','spring','laravel',
    'git','github','gitlab','ci/cd','jenkins','github actions',
    'graphql','rest','api','microservices','grpc','trpc',
    'agile','scrum','jira',
    'figma','photoshop',
    'excel','powerpoint','tableau','power bi',
    'statistical modeling','feature engineering','data modeling',
    'mlflow','bentoml','mlops','kubeflow',
    'dbt','data warehouse','etl',
    'image classification','object detection','speech recognition',
    'gans','lora','weights & biases','tts',
    'apache beam','apache flink',
    'product management','project management','stakeholder management','seo','content writing',
    'data pipelines','android','ios','solidworks','ansys','accounting','sales',
  ];

  const titlePatterns = [
    'machine learning engineer','ml engineer','data engineer','full stack developer',
    'frontend engineer','backend engineer','software engineer','product manager',
    'business analyst','mobile developer','operations manager','marketing manager',
  ];
  titlePatterns.forEach(pattern => {
    if (makeSkillRegex(pattern).test(jdText)) addUnique(signals.titleKeywords, pattern);
  });

  sections.forEach(line => {
    const lineLower = line.toLowerCase().trim();
    if (/required|requirements?|must[\s-]have|essential|mandatory|minimum qualification/i.test(lineLower)) currentSection = 'required';
    else if (/preferred|nice[\s-]to[\s-]have|bonus|optional|desired|good[\s-]to[\s-]have/i.test(lineLower)) currentSection = 'preferred';
    else if (/about|role|responsibilit|what\s+you|benefit|location|salary/i.test(lineLower)) currentSection = 'general';

    const lineSkills = [];
    skillPatterns.forEach(pattern => {
      const regex = makeSkillRegex(pattern);
      if (regex.test(line)) {
        const skillName = canonicalSkill(pattern);
        addUnique(lineSkills, skillName);
        if (currentSection === 'required') {
          addUnique(signals.requiredSkills, skillName);
        } else if (currentSection === 'preferred') {
          addUnique(signals.preferredSkills, skillName);
        }
        addUnique(signals.allSkills, skillName);
      }
    });

    if (lineSkills.length >= 2 && /\b(or similar|or equivalent|any of|one of|either)\b/i.test(lineLower)) {
      addOrGroup(signals.orGroups, lineSkills);
    }
  });

  // Deduplicate: remove preferred skills that are already in required
  if (signals.requiredSkills.length > 0 && signals.preferredSkills.length > 0) {
    signals.preferredSkills = signals.preferredSkills.filter(ps =>
      !signals.requiredSkills.some(rs => normalizeSkillName(rs) === normalizeSkillName(ps))
    );
  }

  // If no required/preferred section found, treat all as required
  if (signals.requiredSkills.length === 0 && signals.allSkills.length > 0) {
    signals.requiredSkills = [...signals.allSkills];
  }

  // Extract Role Family
  let roleFamily = 'general_software';
  const titleKeywordsStr = signals.titleKeywords.join(' ').toLowerCase();
  if (titleKeywordsStr.includes('machine learning') || titleKeywordsStr.includes('ml engineer') || titleKeywordsStr.includes('ml_engineer')) roleFamily = 'ml_engineer';
  else if (titleKeywordsStr.includes('data engineer')) roleFamily = 'data_engineer';
  else if (titleKeywordsStr.includes('full stack') || titleKeywordsStr.includes('fullstack')) roleFamily = 'fullstack';
  else if (titleKeywordsStr.includes('frontend')) roleFamily = 'frontend';
  else if (titleKeywordsStr.includes('backend')) roleFamily = 'backend';
  else if (titleKeywordsStr.includes('product manager')) roleFamily = 'pm';
  else if (titleKeywordsStr.includes('operations')) roleFamily = 'operations';
  else if (titleKeywordsStr.includes('marketing')) roleFamily = 'marketing';
  else if (titleKeywordsStr.includes('business analyst')) roleFamily = 'business_analyst';
  else {
    // Fallback: Check skills list
    const skillsStr = signals.allSkills.map(s => s.toLowerCase());
    if (skillsStr.includes('pytorch') || skillsStr.includes('tensorflow') || skillsStr.includes('machine learning')) roleFamily = 'ml_engineer';
    else if (skillsStr.includes('spark') || skillsStr.includes('airflow') || skillsStr.includes('pyspark')) roleFamily = 'data_engineer';
    else if (skillsStr.includes('react') || skillsStr.includes('angular') || skillsStr.includes('vue') || skillsStr.includes('next.js')) roleFamily = 'frontend';
  }
  signals.roleFamily = roleFamily;

  // Extract Constraints
  let noticePeriodMax = null;
  if (/immediate/i.test(jdText)) {
    noticePeriodMax = 30;
  } else {
    const noticeMatch = jdText.match(/(?:join\s+within\s+(\d+)\s*days?|notice\s+period\s*(?:of|max|up to)?\s*(\d+)\s*days?)/i);
    if (noticeMatch) {
      noticePeriodMax = parseInt(noticeMatch[2] || noticeMatch[1]);
    }
  }

  let workMode = null;
  let workModeRequired = false;
  if (/\bremote\b/i.test(jdText)) workMode = 'remote';
  else if (/\bhybrid\b/i.test(jdText)) workMode = 'hybrid';
  else if (/\b(onsite|on-site|office)\b/i.test(jdText)) workMode = 'onsite';
  if (workMode) {
    workModeRequired = /\b(?:must|mandatory|required|only|strictly)\b.{0,24}\b(?:remote|hybrid|onsite|on-site|office)\b|\b(?:remote|hybrid|onsite|on-site|office)\b.{0,24}\b(?:must|mandatory|required|only|strictly)\b/i.test(jdText);
  }

  let location = null;
  let locationRequired = false;
  const commonLocations = ['Bangalore', 'Bengaluru', 'Hyderabad', 'Mumbai', 'Chennai', 'Delhi', 'Noida', 'Gurgaon', 'Pune', 'Toronto', 'USA', 'India'];
  for (const loc of commonLocations) {
    if (new RegExp('\\b' + loc + '\\b', 'i').test(jdText)) {
      location = loc;
      locationRequired = new RegExp(`\\b(?:must|mandatory|required|only|strictly)\\b.{0,30}\\b${loc}\\b|\\b${loc}\\b.{0,30}\\b(?:must|mandatory|required|only|strictly)\\b`, 'i').test(jdText);
      break;
    }
  }

  let salaryMax = null;
  const lpaMatch = jdText.match(/(?:budget|salary|compensation|package)\D*(\d+)\s*-\s*(\d+)\s*lpa/i) || jdText.match(/(?:up\s+to|max|budget)\D*(\d+)\s*lpa/i);
  if (lpaMatch) {
    salaryMax = parseFloat(lpaMatch[2] || lpaMatch[1]);
  }

  signals.constraints = { noticePeriodMax, workMode, workModeRequired, location, locationRequired, salaryMax };

  // Extract "OR" groups — efficient targeted approach
  // Only look for "X or Y" / "X / Y" patterns in the JD text using detected skills
  const detectedSkillPatterns = signals.allSkills.map(s => {
    // Find original pattern that matched this canonical skill
    const original = skillPatterns.find(p => canonicalSkill(p) === s) || s;
    return { canonical: s, pattern: original };
  });

  for (let i = 0; i < detectedSkillPatterns.length; i++) {
    for (let j = i + 1; j < detectedSkillPatterns.length; j++) {
      const s1 = detectedSkillPatterns[i];
      const s2 = detectedSkillPatterns[j];
      const escaped1 = s1.pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const escaped2 = s2.pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const b1 = skillBoundaries(s1.pattern);
      const b2 = skillBoundaries(s2.pattern);
      // Check "skill1 or skill2" and "skill1 / skill2"
      const regexStr = b1.startBoundary + escaped1 + b1.endBoundary + '\\s+(?:or|\\/)\\s+' + escaped2 + b2.endBoundary;
      const regex = new RegExp(regexStr, 'i');
      if (regex.test(jdText)) {
        addOrGroup(signals.orGroups, [s1.canonical, s2.canonical]);
      }
      // Also check reverse order
      const regexStr2 = b2.startBoundary + escaped2 + b2.endBoundary + '\\s+(?:or|\\/)\\s+' + escaped1 + b1.endBoundary;
      const regex2 = new RegExp(regexStr2, 'i');
      if (regex2.test(jdText)) {
        addOrGroup(signals.orGroups, [s1.canonical, s2.canonical]);
      }
    }
  }

  return signals;
}
