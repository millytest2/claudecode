const els = {
  brandName: document.getElementById('brandName'),
  audience: document.getElementById('audience'),
  tone: document.getElementById('tone'),
  signature: document.getElementById('signature'),
  source: document.getElementById('source'),
  goal: document.getElementById('goal'),
  variations: document.getElementById('variations'),
  platforms: document.getElementById('platforms'),
  researchWindow: document.getElementById('researchWindow'),
  nicheKeywords: document.getElementById('nicheKeywords'),
  accounts: document.getElementById('accounts'),
  winningPosts: document.getElementById('winningPosts'),
  output: document.getElementById('output'),
  generateBtn: document.getElementById('generateBtn'),
  copyAllBtn: document.getElementById('copyAllBtn'),
  exportBtn: document.getElementById('exportBtn'),
  clearBtn: document.getElementById('clearBtn'),
};

const STORAGE_KEY = 'creatorOS.profile.v2';

const platformIntel = {
  'X / Threads': {
    algorithmSignals: ['Strong first line in 1 sentence', 'Early replies + conversation depth', 'Tight, skimmable formatting'],
    hookTypes: ['Contrarian claim', 'Process teardown', 'Mini case study'],
    ctaStyles: ['Ask a binary question', 'Invite reply keyword', 'Prompt quote-retweet'],
    bucketIdeas: ['Hot take', 'Framework thread', 'Lessons learned', 'Build in public update'],
    researchQueries: ['site:x.com "your niche" "thread"', 'Search by top posts in last 7 days', 'Track top 20 hooks from competitor accounts'],
    cadence: '2-4 posts/day + 1 thread every 2-3 days',
  },
  LinkedIn: {
    algorithmSignals: ['Dwell time from strong formatting', 'Comment quality over vanity likes', 'Expertise + story blend'],
    hookTypes: ['Career pain point', 'Myth busting', 'Before/after results'],
    ctaStyles: ['Ask for opinion in comments', 'Offer checklist via comment keyword', 'Invite DM for framework'],
    bucketIdeas: ['Professional lesson', 'Client story', 'Point of view post', 'Industry trend breakdown'],
    researchQueries: ['LinkedIn search + sort by recent', 'Capture top 10 creators in niche and weekly winners', 'Save comment-rich posts with similar audience'],
    cadence: '1 high-quality post/day',
  },
  'Instagram Caption': {
    algorithmSignals: ['Watch time/rewatches (for reels)', 'Saves + shares', 'Clear visual hook + caption value'],
    hookTypes: ['Pain > promise', 'Step-by-step teaser', 'Relatable confession'],
    ctaStyles: ['Save for later', 'Comment keyword', 'Share with a friend'],
    bucketIdeas: ['Carousel tips', 'Reel education', 'Behind the scenes', 'Proof screenshot story'],
    researchQueries: ['Explore page niche hashtag scan', 'Track top reels by saves/shares', 'Collect 15 recurring caption hooks'],
    cadence: '1 reel/day + 2-3 carousels/week',
  },
  'TikTok Script': {
    algorithmSignals: ['Retention at first 3 seconds', 'Completion rate', 'Loopability and comments'],
    hookTypes: ['Direct callout', 'Shock stat', 'POV scenario'],
    ctaStyles: ['Comment part 2', 'Follow for daily systems', 'Keyword DM funnel'],
    bucketIdeas: ['Quick how-to', 'Storytime lesson', 'Myth vs reality', 'Tool/tutorial demo'],
    researchQueries: ['TikTok Creative Center trends', 'Search niche keyword + filter this week', 'Log recurring editing patterns on top clips'],
    cadence: '1-3 videos/day',
  },
  'YouTube Short': {
    algorithmSignals: ['Swipe-stop rate', 'Average view percentage', 'Clear payoff by second 30'],
    hookTypes: ['Bold promise', 'Mistake to avoid', 'Challenge format'],
    ctaStyles: ['Watch related long-form', 'Subscribe for series', 'Comment your situation'],
    bucketIdeas: ['60-second tutorial', 'Mistakes list', 'Case-study snippet', 'Template walkthrough'],
    researchQueries: ['YouTube search > filter this month + views', 'Analyze titles with high views/subscriber ratio', 'Map best-performing intro patterns'],
    cadence: '1 short/day, then double down on top 20%',
  },
  Email: {
    algorithmSignals: ['Open rate via subject specificity', 'Click-through from one clear CTA', 'Reply rate from conversational tone'],
    hookTypes: ['Single curiosity hook', 'Strong opinion', 'Problem-solution angle'],
    ctaStyles: ['One link one action', 'Reply prompt', 'Soft sell CTA'],
    bucketIdeas: ['Weekly insights digest', 'Tactical mini lesson', 'Offer story', 'Audience Q&A answer'],
    researchQueries: ['Review top opened subjects from last sends', 'Tag emails by click/reply outcome', 'Maintain swipe file of winning intros'],
    cadence: '2-5 emails/week',
  },
};

const templates = {
  'X / Threads': [
    ({ hook, insight, cta, voice }) => `${hook}\n\n${insight}\n\n${voice}\n\n${cta}`,
    ({ hook, bullets, cta }) => `${hook}\n\n${bullets.map((b) => `• ${b}`).join('\n')}\n\n${cta}`,
  ],
  LinkedIn: [
    ({ hook, insight, bullets, cta }) => `${hook}\n\nMost people overcomplicate this.\n\n${insight}\n\n${bullets.map((b) => `- ${b}`).join('\n')}\n\n${cta}`,
    ({ hook, insight, voice, cta }) => `${hook}\n\n${insight}\n\nWhat changed for me: ${voice}\n\n${cta}`,
  ],
  'Instagram Caption': [
    ({ hook, insight, cta }) => `${hook}\n\n${insight}\n\nSave this if you need a simple system.\n\n${cta} #creator #contentstrategy #buildinpublic`,
    ({ hook, bullets, cta }) => `${hook}\n\n${bullets.join(' ✦ ')}\n\n${cta} #marketing #growth #solopreneur`,
  ],
  'TikTok Script': [
    ({ hook, bullets, cta }) => `HOOK: ${hook}\n\nSCRIPT:\n${bullets.map((b, i) => `${i + 1}) ${b}`).join('\n')}\n\nCLOSE: ${cta}`,
    ({ hook, insight, cta }) => `On-screen text: ${hook}\n\nTalking points:\n${insight}\n\nFinal line: ${cta}`,
  ],
  'YouTube Short': [
    ({ hook, bullets, cta }) => `Title idea: ${hook}\n\n0-5s: ${bullets[0]}\n5-20s: ${bullets[1]}\n20-40s: ${bullets[2]}\n40-55s: ${bullets[3]}\n55-60s: ${cta}`,
    ({ hook, insight, cta }) => `Title idea: ${hook}\n\nOne-minute script:\n${insight}\n\nOutro: ${cta}`,
  ],
  Email: [
    ({ hook, insight, bullets, cta, audience }) => `Subject: ${hook}\n\nHey ${audience || 'there'},\n\n${insight}\n\n${bullets.map((b) => `- ${b}`).join('\n')}\n\n${cta}\n`,
    ({ hook, insight, cta }) => `Subject: ${hook}\n\nQuick one today:\n\n${insight}\n\n${cta}`,
  ],
};

function saveProfile() {
  const payload = {
    brandName: els.brandName.value,
    audience: els.audience.value,
    tone: els.tone.value,
    signature: els.signature.value,
    researchWindow: els.researchWindow.value,
    nicheKeywords: els.nicheKeywords.value,
    accounts: els.accounts.value,
    winningPosts: els.winningPosts.value,
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
}

function loadProfile() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return;
  try {
    const data = JSON.parse(raw);
    Object.keys(data).forEach((key) => {
      if (els[key]) {
        els[key].value = data[key];
      }
    });
  } catch (err) {
    console.warn('Could not parse saved profile.', err);
  }
}

function sentenceChunks(text) {
  return text
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function getWinningHooks() {
  return els.winningPosts.value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .slice(0, 5);
}

function buildMaterial() {
  const source = els.source.value.trim();
  const chunks = sentenceChunks(source);
  const tone = els.tone.value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  const hook = chunks[0] || `How ${els.brandName.value || 'creators'} can ${els.goal.value.toLowerCase()} with less effort`;
  const insight = chunks.slice(1, 4).join(' ') || source;
  const bullets = [
    chunks[1] || 'Pick one platform and one clear promise',
    chunks[2] || 'Turn one core idea into multiple angles',
    chunks[3] || 'Use repeatable templates instead of starting from zero',
    chunks[4] || 'Review results weekly and double down on what converts',
  ];

  const voice = [
    tone.length ? `Tone: ${tone.slice(0, 3).join(', ')}.` : 'Tone: clear, human, practical.',
    els.signature.value ? `Signature: ${els.signature.value}` : '',
  ]
    .filter(Boolean)
    .join(' ');

  const ctaMap = {
    'Grow audience': 'Follow for daily systems you can actually execute.',
    'Build trust': 'Reply "plan" and I will share the framework I use each week.',
    'Drive traffic': 'Read the full breakdown at the link in bio.',
    'Generate leads': 'DM me "scale" if you want this workflow template.',
    'Sell offer': 'If you want help implementing this, send me "ready".',
  };

  return {
    hook,
    insight,
    bullets,
    voice,
    cta: ctaMap[els.goal.value],
    audience: els.audience.value || 'friend',
  };
}

function selectedPlatforms() {
  return Array.from(els.platforms.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
}

function buildResearchAgentPlan(platform, intel, winningHooks) {
  const keywords = els.nicheKeywords.value || 'your niche keywords';
  const accounts = els.accounts.value || 'top creators + direct competitors';

  return [
    `### Research Agent Sprint (${platform})`,
    `Time window: Last ${els.researchWindow.value} days`,
    `Keywords: ${keywords}`,
    `Accounts to track: ${accounts}`,
    'Actions:',
    `1) Collect 20 recent high-performing examples for ${platform}.`,
    '2) Tag each example by: hook type, format, CTA, and sentiment angle.',
    '3) Rank top 5 patterns by frequency + engagement quality.',
    '4) Write 3 experiments you can run this week based on those patterns.',
    winningHooks.length ? `Reference winners you provided: ${winningHooks.join(' | ')}` : 'Reference winners you provided: none yet.',
    '',
    'Suggested search tactics:',
    ...intel.researchQueries.map((q) => `- ${q}`),
  ].join('\n');
}

function buildPlatformBuckets(platform, material, winningHooks) {
  const intel = platformIntel[platform];
  if (!intel) return '';

  const winningLine = winningHooks.length ? winningHooks.map((h) => `- ${h}`).join('\n') : '- (Add winning examples in Research Agent Inputs to personalize this section)';

  return [
    `## ${platform} — Strategy Buckets`,
    `Cadence target: ${intel.cadence}`,
    '',
    'Bucket A: What Is Working Right Now',
    ...intel.algorithmSignals.map((x) => `- ${x}`),
    '',
    'Bucket B: Hook Angles To Test',
    ...intel.hookTypes.map((x) => `- ${x}`),
    '',
    'Bucket C: CTA Patterns',
    ...intel.ctaStyles.map((x) => `- ${x}`),
    '',
    'Bucket D: Content Pillars / Series Ideas',
    ...intel.bucketIdeas.map((x) => `- ${x}`),
    '',
    'Bucket E: Your Current Winner Inputs',
    winningLine,
    '',
    buildResearchAgentPlan(platform, intel, winningHooks),
    '',
    `## ${platform} — Draft Outputs`,
    `Primary hook: ${material.hook}`,
    '',
  ].join('\n');
}

function generate() {
  const source = els.source.value.trim();
  if (!source) {
    els.output.textContent = 'Please paste source content first.';
    return;
  }

  saveProfile();
  const base = buildMaterial();
  const platforms = selectedPlatforms();
  const count = Math.max(1, Math.min(5, Number(els.variations.value) || 1));
  const winningHooks = getWinningHooks();

  const output = [];
  output.push(`# Creator OS Output — ${new Date().toLocaleString()}`);
  output.push(`Brand: ${els.brandName.value || 'N/A'} | Goal: ${els.goal.value}`);
  output.push(`Research window: last ${els.researchWindow.value} days`);
  output.push('');

  platforms.forEach((platform) => {
    output.push(buildPlatformBuckets(platform, base, winningHooks));
    const set = templates[platform] || [];
    for (let i = 0; i < count; i += 1) {
      const template = set[i % set.length];
      output.push(`Variation ${i + 1}`);
      output.push(template(base));
      output.push('');
    }
    output.push('---');
    output.push('');
  });

  els.output.textContent = output.join('\n');
}

function copyAll() {
  const text = els.output.textContent.trim();
  if (!text) return;
  navigator.clipboard.writeText(text);
}

function exportTxt() {
  const text = els.output.textContent.trim();
  if (!text) return;
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `creator-os-${Date.now()}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
}

function clearAll() {
  els.source.value = '';
  els.winningPosts.value = '';
  els.output.innerHTML = '<p class="muted">Your generated content will appear here.</p>';
  saveProfile();
}

loadProfile();
els.generateBtn.addEventListener('click', generate);
els.copyAllBtn.addEventListener('click', copyAll);
els.exportBtn.addEventListener('click', exportTxt);
els.clearBtn.addEventListener('click', clearAll);
['brandName', 'audience', 'tone', 'signature', 'researchWindow', 'nicheKeywords', 'accounts', 'winningPosts'].forEach((key) => {
  els[key].addEventListener('input', saveProfile);
});
