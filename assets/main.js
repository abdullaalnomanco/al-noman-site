// ---- Theme toggle ----
const themeBtn = document.getElementById('themeToggle');
const root = document.documentElement;
function applyTheme(t){
  root.setAttribute('data-theme', t);
  if (themeBtn) themeBtn.textContent = t === 'dark' ? 'Light' : 'Dark';
  localStorage.setItem('theme', t);
}
applyTheme(localStorage.getItem('theme') || 'light');
if (themeBtn) themeBtn.addEventListener('click', () => {
  applyTheme(root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
});

// ---- Mobile menu ----
const menuBtn = document.getElementById('menuBtn');
const navLinks = document.getElementById('navLinks');
if (menuBtn && navLinks){
  menuBtn.addEventListener('click', () => {
    const open = navLinks.classList.toggle('open');
    menuBtn.setAttribute('aria-expanded', open);
  });
  navLinks.querySelectorAll('a').forEach(a => a.addEventListener('click', () => {
    navLinks.classList.remove('open');
    menuBtn.setAttribute('aria-expanded', false);
  }));
}

// ---- Scroll progress + active nav + back-to-top ----
const progress = document.getElementById('progress');
const toTop = document.getElementById('toTop');
const navA = navLinks ? [...navLinks.querySelectorAll('a')] : [];
const sections = navA.map(a => {
  const href = a.getAttribute('href');
  return href && href.startsWith('#') ? document.querySelector(href) : null;
});

window.addEventListener('scroll', () => {
  const h = document.documentElement;
  const pct = (h.scrollTop) / (h.scrollHeight - h.clientHeight) * 100;
  if (progress) progress.style.width = pct + '%';
  if (toTop) toTop.classList.toggle('show', h.scrollTop > 600);
  let current = null;
  sections.forEach((sec, i) => { if (sec && sec.getBoundingClientRect().top < 140) current = i; });
  navA.forEach((a, i) => a.classList.toggle('active', i === current));
}, { passive: true });

if (toTop) toTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

// ---- Reveal on scroll ----
const revealEls = document.querySelectorAll('.reveal, .tl-item');
const io = new IntersectionObserver((entries) => {
  entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('in'); });
}, { threshold: 0.15 });
revealEls.forEach(el => io.observe(el));

// ---- Research accordion ----
document.querySelectorAll('.paper-head').forEach(btn => {
  btn.addEventListener('click', () => {
    const paper = btn.closest('.paper');
    const isOpen = paper.classList.contains('open');
    document.querySelectorAll('.paper.open').forEach(p => {
      p.classList.remove('open');
      p.querySelector('.paper-head').setAttribute('aria-expanded', 'false');
    });
    if (!isOpen){ paper.classList.add('open'); btn.setAttribute('aria-expanded', 'true'); }
  });
});

// ---- Research filter ----
document.querySelectorAll('.filter-row .filter-btn').forEach(btn => {
  if (btn.closest('#journeyFilters')) return; // handled separately below
  btn.addEventListener('click', () => {
    const row = btn.closest('.filter-row');
    row.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const f = btn.dataset.filter;
    document.querySelectorAll('.paper').forEach(p => {
      p.classList.toggle('hide', f !== 'all' && p.dataset.status !== f);
    });
  });
});

const tooltip = document.getElementById('tooltip');
function hideTip(){ if (tooltip) tooltip.classList.remove('show'); }

// ---- Journey map (only runs if the journey chart exists on this page) ----
const jSvg = document.getElementById('journeySvg');
const yearGrid = document.getElementById('yearGrid');

if (jSvg && yearGrid){
  const jStart = 2017, jEnd = 2027, jX0 = 60, jX1 = 860;
  const yearX = (y) => jX0 + (y - jStart) / (jEnd - jStart) * (jX1 - jX0);

  for (let y = jStart; y <= jEnd; y++){
    const x = yearX(y);
    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', x); line.setAttribute('x2', x);
    line.setAttribute('y1', 14); line.setAttribute('y2', 256);
    line.setAttribute('stroke', 'var(--rule)'); line.setAttribute('stroke-width', '1');
    yearGrid.appendChild(line);
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('x', x); label.setAttribute('y', 270);
    label.setAttribute('font-family', 'IBM Plex Mono'); label.setAttribute('font-size', '9');
    label.setAttribute('font-weight', '600'); label.setAttribute('fill', 'var(--ink-soft)');
    label.setAttribute('text-anchor', 'middle');
    label.textContent = y;
    yearGrid.appendChild(label);
  }

  const journeyPoints = [
    { year: 2017, lane: 'academic', y: 90, tier: 0, name: ['Jubilee High', 'SSC'],
      title: 'Secondary School Certificate, Science', org: 'Patuakhali Govt. Jubilee High School',
      detail: 'Completed secondary education in the Science track, Patuakhali, Bangladesh.' },
    { year: 2019, lane: 'academic', y: 90, tier: 1, name: ['Patuakhali Govt.', 'College — HSC'],
      title: 'Higher Secondary Certificate, Science', org: 'Patuakhali Govt. College',
      detail: 'Completed higher secondary education in the Science track, ahead of starting a Computer Science degree.' },
    { year: 2020,  lane: 'academic', y: 90, tier: 0, name: ['Daffodil Intl.', '2020–24'],
      title: 'BSc Computer Science & Engineering', org: 'Daffodil International University',
      detail: 'Served as General Secretary of the DIU Computer Programming Club, organizing 150+ events, and held a performance-based scholarship (2020–2022).' },
    { year: 2022.3, lane: 'academic', y: 90, tier: 1, name: ['FabLab DIU', 'Research Asst.'],
      title: 'Research Assistant', org: 'FabLab, Daffodil International University',
      detail: 'Supported research activities and project work at the FabLab, alongside early design internships.' },
    { year: 2025.0, lane: 'academic', y: 90, tier: 0, name: ['UCA Farnham', 'MSc HCI'],
      title: 'MSc Human-Computer Interaction begins', org: 'University for the Creative Arts, Farnham',
      detail: 'Started the MSc HCI programme, supervised by Roderick Morgan — the start of a formal research track alongside design practice.' },
    { year: 2025.55, lane: 'academic', y: 90, tier: 1, name: ['BubbleDo', 'SUS 84.0'],
      title: 'BubbleDo — spatial task manager', org: 'UCA coursework project (FGCT7022)',
      detail: 'A spatial task manager scored 84.0 on the System Usability Scale — the "Excellent" band — with 9 of 10 participants spontaneously grouping tasks spatially.' },
    { year: 2026.05, lane: 'academic', y: 90, tier: 0, name: ['Adaptive VR', '8.25/10'],
      title: 'Adaptive VR Workspace', org: 'UCA coursework project (FGCT7023)',
      detail: 'Four mood-responsive VR environments, tested with a postgraduate design cohort at a mean perceived productivity of 8.25/10.' },
    { year: 2026.5, lane: 'academic', y: 90, tier: 1, name: ['CITDI 2026', 'Accepted'],
      title: 'First peer-reviewed paper accepted', org: 'Springer / EAI, Scopus-indexed',
      detail: 'Statistical analysis of 10,303 Google Play reviews — the first formal publication credential on the PhD pathway.' },
    { year: 2027, lane: 'academic', y: 90, tier: 0, name: ['PhD', '(target)'], future: true,
      title: 'PhD — target start', org: 'Human-AI Interaction & Trustworthy AI',
      detail: 'Targeting a September 2027 start, building on the FMP work in trust calibration and explainability.' },

    { year: 2022.1, lane: 'professional', y: 190, tier: 0, name: ['Corporate Ask'],
      title: 'Intern, Graphic Designer', org: 'Corporate Ask',
      detail: 'First professional design role — designing intuitive interactions and iterating on continuous user testing.' },
    { year: 2022.6, lane: 'professional', y: 190, tier: 1, name: ['Beeo Digital'],
      title: 'Intern, UX/UI Designer', org: 'Beeo Digital',
      detail: 'Conducted user research to understand user needs and iterated designs based on continuous testing.' },
    { year: 2023.6, lane: 'professional', y: 190, tier: 0, name: ['Devlab Solution'],
      title: 'UI/UX Designer', org: 'Devlab Solution',
      detail: 'Wireframing, prototyping, and interaction design across multiple end-to-end design projects.' },
    { year: 2024.3, lane: 'professional', y: 190, tier: 1, name: ['PixelPlo', 'Georgia DHS'],
      title: 'Senior Visualizer', org: 'PixelPlo',
      detail: 'Sole designer on the Georgia DHS Document Digitization & Search Solution with EBIW — natural-language query, OTP-protected downloads, OCR/vectorization flows. Named Employee of the Month.' },
    { year: 2025.3, lane: 'professional', y: 190, tier: 0, name: ['Hellotask', 'Head of Design'],
      title: 'Head of Design', org: 'Hellotask Technologies Ltd',
      detail: 'Leading the end-to-end design process, building a scalable design system, and mentoring the design team — current role.' }
  ];

  const tierOffset = { academic: [14, 34], professional: [14, 34] };
  const lineH = 11;

  const jNodesG = document.getElementById('journeyNodes');
  journeyPoints.forEach((p, i) => {
    p._id = i;
    const x = yearX(p.year);
    const color = p.lane === 'academic' ? 'var(--accent)' : 'var(--ink)';
    const laneClass = p.lane === 'academic' ? 'lane-academic-el' : 'lane-professional-el';

    const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    c.setAttribute('cx', x); c.setAttribute('cy', p.y); c.setAttribute('r', 5.5);
    c.setAttribute('class', 'jnode ' + laneClass + (p.future ? ' future' : ''));
    c.setAttribute('fill', p.future ? 'var(--paper-raised)' : color);
    c.setAttribute('stroke', color); c.setAttribute('stroke-width', p.future ? '2.5' : '0');
    c.setAttribute('tabindex', '0');
    c.dataset.id = i;
    c.addEventListener('mouseenter', (e) => showJourneyTip(e, p));
    c.addEventListener('mouseleave', hideTip);
    c.addEventListener('click', () => selectJourneyNode(p, c));
    c.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' '){ e.preventDefault(); selectJourneyNode(p, c); } });
    jNodesG.appendChild(c);

    const baseOffset = tierOffset[p.lane][p.tier];
    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('x', x);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('font-family', 'IBM Plex Mono');
    text.setAttribute('font-size', '9');
    text.setAttribute('font-weight', '700');
    text.setAttribute('fill', 'var(--ink)');
    text.setAttribute('class', 'jname ' + laneClass);
    p.name.forEach((line, li) => {
      const tspan = document.createElementNS('http://www.w3.org/2000/svg', 'tspan');
      tspan.setAttribute('x', x);
      const dist = baseOffset + (p.name.length - 1 - li) * lineH;
      const baseY = p.lane === 'academic' ? p.y - dist : p.y + dist + 6;
      tspan.setAttribute('y', baseY);
      tspan.textContent = line;
      text.appendChild(tspan);
    });
    jNodesG.appendChild(text);
  });

  function showJourneyTip(e, p){
    const rect = jSvg.getBoundingClientRect();
    const cx = e.target.getAttribute('cx') / 900 * rect.width;
    const cy = e.target.getAttribute('cy') / 280 * rect.height;
    tooltip.textContent = `${p.name.join(' ')} — click for details`;
    tooltip.style.left = (rect.left + window.scrollX + cx + 12) + 'px';
    tooltip.style.top = (rect.top + window.scrollY + cy - 10) + 'px';
    tooltip.classList.add('show');
  }

  const jdEyebrow = document.getElementById('jdEyebrow');
  const jdTitle = document.getElementById('jdTitle');
  const jdBody = document.getElementById('jdBody');
  function selectJourneyNode(p, el){
    document.querySelectorAll('.jnode.selected').forEach(n => n.classList.remove('selected'));
    el.classList.add('selected');
    if (jdEyebrow) jdEyebrow.textContent = (p.lane === 'academic' ? 'Academic · ' : 'Professional · ') + Math.floor(p.year);
    if (jdTitle) jdTitle.textContent = p.title;
    if (jdBody) jdBody.textContent = p.org + ' — ' + p.detail;
    hideTip();
  }

  document.querySelectorAll('#journeyFilters .filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#journeyFilters .filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const lane = btn.dataset.lane;
      jSvg.classList.remove('filter-academic', 'filter-professional');
      if (lane === 'academic') jSvg.classList.add('filter-professional');
      if (lane === 'professional') jSvg.classList.add('filter-academic');
    });
  });
}

// ---- Achievement counters (only run if present on this page) ----
const achvNums = document.querySelectorAll('.achv-num');
if (achvNums.length){
  const achvIo = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el = entry.target;
      achvIo.unobserve(el);
      const target = parseFloat(el.dataset.target);
      const suffix = el.dataset.suffix || '';
      const decimals = el.dataset.decimal ? parseInt(el.dataset.decimal) : 0;
      const duration = 1200;
      const start = performance.now();
      function tick(now){
        const p = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - p, 3);
        const val = target * eased;
        el.textContent = (decimals ? val.toFixed(decimals) : Math.round(val).toLocaleString()) + suffix;
        if (p < 1) requestAnimationFrame(tick);
      }
      requestAnimationFrame(tick);
    });
  }, { threshold: 0.4 });
  achvNums.forEach(el => achvIo.observe(el));
}
