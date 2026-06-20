import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const API = '/api';
const PERIODS = ['Morgen', 'Nachmittag', 'Abend', 'Nacht'];
const ROUTES = ['aurora', 'brummbert', 'mira'];
const ROUTE_META = {
  aurora: { name: 'Aurora 7000', color: '#ffbf46', colorHex: 0xffbf46, mood: 'vorsichtig neugierig' },
  brummbert: { name: 'Brummbert', color: '#f36d3d', colorHex: 0xf36d3d, mood: 'warm beschuetzend' },
  mira: { name: 'Mira Schaufelstern', color: '#9b7cff', colorHex: 0x9b7cff, mood: 'traeumerisch forschend' },
};
const ENDING_KIND_LABELS = {
  bad: 'Bad End', missed: 'Missed Route', friendship: 'Friendship End',
  normal: 'Normal Romance End', true: 'True Romance End', secret: 'Secret End',
};

let state = null, gameData = null, settings = null;
let serverSaveToken = localStorage.getItem('bagger_last_token') || '';
let isTyping = false, isWaiting = false, autoMode = false, skipMode = false;
let currentScene = null, currentVisual = null;
let autoTimer = null, backlog = [];
let modelScene = null, modelRenderer = null, modelMesh = null;
let modelAnimId = null;
let hideUI = false, lastRouteGuide = null;

const $ = s => document.querySelector(s);
const $$ = s => document.querySelectorAll(s);

let D = {
  screen: id => $(`#screen-${id}`),
  mainMenu: () => $('#screen-main-menu'),
  setup: () => $('#screen-setup'),
  adv: () => $('#screen-adv'),
  nvl: () => $('#screen-nvl'),
  ending: () => $('#screen-ending'),
  textbox: () => $('#textbox'),
  dialogueText: () => $('#dialogue-text'),
  ctc: () => $('#ctc-indicator'),
  nameplate: () => $('#nameplate'),
  speakerName: () => $('#speaker-name'),
  speakerMood: () => $('#speaker-mood'),
  choices: () => $('#choices'),
  freeTextArea: () => $('#free-text-area'),
  talkForm: () => $('#talk-form'),
  freeMessage: () => $('#free-message'),
  advCharacter: () => $('#adv-character'),
  modelStage: () => $('#model-stage'),
  locationName: () => $('#location-name'),
  locationFit: () => $('#location-fit'),
  routePhase: () => $('#route-phase'),
  dayDisplay: () => $('#day-display'),
  periodDisplay: () => $('#period-display'),
  lockDisplay: () => $('#lock-display'),
  calendarTag: () => $('#calendar-tag'),
  endingCard: () => $('#ending-card'),
  sceneTransition: () => $('#scene-transition'),
  locCard: () => $('#location-title-card'),
  locCardTitle: () => $('#loc-card-title'),
  locCardSub: () => $('#loc-card-sub'),
  routeSelectBar: () => $('#route-select-bar'),
  nvlLines: () => $('#nvl-lines'),
  nvlCtc: () => $('#nvl-ctc'),
  nvlChoices: () => $('#nvl-choices'),
  guideCard: () => $('#route-guide-card'),
  guideStage: () => $('#guide-stage'),
  guideGoal: () => $('#guide-goal'),
  actionFeedback: () => $('#action-feedback'),
};

/* ═══════════════════════════════════════
   API
   ═══════════════════════════════════════ */
async function apiPost(path, body) {
  const r = await fetch(API + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
  return r.json();
}
async function apiGet(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`API ${path}: ${r.status}`);
  return r.json();
}

/* ═══════════════════════════════════════
   SCREEN MANAGER
   ═══════════════════════════════════════ */
function showScreen(id) {
  $$('.screen, .fullscreen-screen, .overlay-screen').forEach(s => s.classList.add('hidden'));
  const el = D.screen(id);
  if (el) el.classList.remove('hidden');
}
function showOverlay(id) {
  const el = D.screen(id);
  if (el) el.classList.remove('hidden');
}
function hideOverlay(id) {
  const el = D.screen(id);
  if (el) el.classList.add('hidden');
}

/* ═══════════════════════════════════════
   TYPEWRITER
   ═══════════════════════════════════════ */
function getTextSpeed() {
  const s = settings ? settings.textSpeed : 35;
  return Math.max(10, 80 - s + 10);
}
async function typeText(el, text, speed) {
  if (!el) return;
  el.textContent = '';
  isTyping = true;
  isWaiting = false;
  const ms = speed || getTextSpeed();
  const chars = [...text];
  for (let i = 0; i < chars.length; i++) {
    if (!isTyping) { el.textContent = text; break; }
    el.textContent += chars[i];
    if (chars[i] === ' ' || chars[i] === '\n') continue;
    if (chars[i] === '.' || chars[i] === '!' || chars[i] === '?') await sleep(ms * 3);
    else if (chars[i] === ',' || chars[i] === ';') await sleep(ms * 1.5);
    else await sleep(ms);
  }
  isTyping = false;
  isWaiting = true;
}
function skipTyping() {
  if (isTyping) isTyping = false;
}
function sleep(ms) {
  return new Promise(r => { if (!isTyping) return r(); setTimeout(r, ms); });
}

/* ═══════════════════════════════════════
   MAIN MENU
   ═══════════════════════════════════════ */
async function initMenuThree() {
  const canvas = document.getElementById('menu-canvas');
  if (!canvas) return;
  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true });
  const w = window.innerWidth, h = window.innerHeight;
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, w / h, 0.1, 100);
  camera.position.z = 22;

  const particlesGeo = new THREE.BufferGeometry();
  const count = 200;
  const pos = new Float32Array(count * 3);
  const sizes = new Float32Array(count);
  for (let i = 0; i < count; i++) {
    pos[i*3] = (Math.random() - 0.5) * 50;
    pos[i*3+1] = (Math.random() - 0.5) * 30;
    pos[i*3+2] = (Math.random() - 0.5) * 20 - 5;
    sizes[i] = Math.random() * 3 + 1;
  }
  particlesGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  particlesGeo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));

  const particleTex = (() => {
    const c = document.createElement('canvas'); c.width = 32; c.height = 32;
    const ctx = c.getContext('2d');
    const g = ctx.createRadialGradient(16,16,0,16,16,16);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.3, 'rgba(255,191,70,0.6)');
    g.addColorStop(1, 'rgba(255,191,70,0)');
    ctx.fillStyle = g; ctx.fillRect(0,0,32,32);
    return new THREE.CanvasTexture(c);
  })();

  const particleMat = new THREE.PointsMaterial({
    map: particleTex, size: 0.4, blending: THREE.AdditiveBlending,
    depthWrite: false, transparent: true, opacity: 0.8,
  });
  const particles = new THREE.Points(particlesGeo, particleMat);
  scene.add(particles);

  const ringGeo = new THREE.TorusGeometry(4, 0.05, 16, 60);
  const ringMat = new THREE.MeshBasicMaterial({ color: 0xffbf46, transparent: true, opacity: 0.15 });
  const ring = new THREE.Mesh(ringGeo, ringMat);
  ring.rotation.x = Math.PI * 0.5;
  ring.position.y = -1.5;
  scene.add(ring);

  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(6, 0.03, 16, 80), ringMat);
  ring2.material = ringMat.clone();
  ring2.material.color.setHex(0x9b7cff);
  ring2.material.opacity = 0.1;
  ring2.rotation.x = Math.PI * 0.4;
  ring2.rotation.z = 0.3;
  ring2.position.y = 2;
  scene.add(ring2);

  function resize() {
    const ww = window.innerWidth, hh = window.innerHeight;
    renderer.setSize(ww, hh);
    camera.aspect = ww / hh;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);

  let time = 0;
  function anim() {
    animId = requestAnimationFrame(anim);
    time += 0.005;
    const positions = particles.geometry.attributes.position.array;
    for (let i = 0; i < count; i++) {
      positions[i*3+1] += Math.sin(time + i) * 0.002;
      positions[i*3] += Math.cos(time * 0.7 + i * 0.3) * 0.001;
    }
    particles.geometry.attributes.position.needsUpdate = true;
    ring.rotation.z += 0.003;
    ring2.rotation.z -= 0.002;
    renderer.render(scene, camera);
  }
  let animId;
  anim();
}
initMenuThree();

/* ═══════════════════════════════════════
   SETUP / NEW GAME
   ═══════════════════════════════════════ */
async function populateSetup() {
  if (!gameData) return;
  const sel = $('#player-style');
  sel.innerHTML = '';
  for (const [k, v] of Object.entries(gameData.playerStyles || {})) {
    const opt = document.createElement('option');
    opt.value = k; opt.textContent = v.label || k;
    sel.appendChild(opt);
  }
}
$('#setup-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const name = $('#player-name').value.trim() || 'Pilot';
  const address = $('#player-address').value.trim() || 'du';
  const style = $('#player-style').value;
  await startNewGame({ name, address, style });
});
$('#restore-form')?.addEventListener('submit', async e => {
  e.preventDefault();
  const token = $('#restore-token').value.trim();
  if (!token) return;
  try {
    const data = await apiPost('/restore', { token });
    if (data.ok && data.state) {
      serverSaveToken = data.token || token;
      localStorage.setItem('bagger_last_token', serverSaveToken);
      state = data.state;
      settings = state.settings || getDefaultSettings();
      applySettings();
      startGameLoop();
    }
  } catch (err) { console.error('Restore failed:', err); }
});

async function startNewGame(player) {
  try {
    state = null;
    const data = await apiPost('/new-game', { player });
    if (!data.ok || !data.state) throw new Error('new-game failed');
    state = data.state;
    settings = state.settings || getDefaultSettings();
    applySettings();
    await firstAdvance();
  } catch (err) { console.error('new-game:', err); }
}

async function firstAdvance() {
  try {
    const data = await apiPost('/interact', { state, intent: { action: 'advance' } });
    if (!data || !data.state) throw new Error('first interact failed');
    state = data.state;
    settings = state.settings || getDefaultSettings();
    applySettings();
    handleSceneData(data);
    setupAdvancer();
    startGameLoop();
  } catch (err) { console.error('first advance:', err); }
}

function startGameLoop() {
  showScreen('adv');
  updateUI();
  initModelStage();
  loadCharacterModel(state.currentRoute || 'aurora');
  resetAdvancer();
}

/* ═══════════════════════════════════════
   CORE GAME LOOP - ADVANCE
   ═══════════════════════════════════════ */
let advanceLock = false;
async function advance(intentOverride) {
  if (advanceLock) return;
  if (!state) return;
  advanceLock = true;
  stopAuto();
  try {
    const intent = intentOverride || { action: 'advance' };
    const data = await apiPost('/interact', { state, intent });
    if (!data || !data.state) throw new Error('interact failed');
    state = data.state;
    settings = state.settings || getDefaultSettings();
    handleSceneData(data);
    resetAdvancer();
  } catch (err) { console.error('advance:', err); }
  finally { advanceLock = false; }
}

function handleSceneData(data) {
  const { reply, scene, emotionalRead, visual, ending, memory, endingProse, feedback, routeGuide } = data;
  if (routeGuide || feedback?.guide) {
    lastRouteGuide = routeGuide || feedback.guide;
  }

  if (ending) {
    showEndingScreen(ending, endingProse, state);
    return;
  }

  currentScene = scene || null;
  currentVisual = visual || null;

  if (scene && scene.premise) {
    addToBacklog('_narrator_', scene.premise, scene.route, scene.chapter);
  }
  if (reply) {
    const speaker = scene ? ROUTE_META[scene.route]?.name || scene.route : null;
    const mood = emotionalRead || null;
    addToBacklog(speaker, reply, scene?.route || state.currentRoute, scene?.chapter);
    playDialogue(reply, speaker, mood, visual, scene);
  } else {
    finishAdvance(visual, scene);
  }

  if (memory) {
    const route = scene?.route || state.currentRoute;
    if (state.relationships?.[route]?.memories) {
      if (!state.relationships[route].memories.includes(memory)) {
        state.relationships[route].memories.push(memory);
        if (state.relationships[route].memories.length > 24) {
          state.relationships[route].memories.shift();
        }
      }
    }
  }

  updateUI();
  renderRouteGuide(lastRouteGuide || buildLocalRouteGuide(state.currentRoute || scene?.route || 'aurora'));
  renderActionFeedback(feedback);
  if (scene) updateCharacter(scene.route, visual, scene.location);
}

function playDialogue(text, speaker, mood, visual, scene) {
  isWaiting = false;
  const nvlMode = getEffectiveNvlMode(scene);

  if (nvlMode === 'nvl') {
    showNvlDialogue(text, speaker, mood, scene);
  } else {
    showAdvDialogue(text, speaker, mood, scene);
  }
}

function showAdvDialogue(text, speaker, mood, scene) {
  hideOverlay('nvl');
  if (speaker) {
    D.speakerName().textContent = speaker;
    const color = ROUTE_META[scene?.route]?.color || '#ffbf46';
    D.nameplate().style.background = color;
    D.nameplate().style.color = color === '#ffbf46' ? '#160f08' : '#fff';
  }
  D.speakerMood().textContent = mood || '';
  D.nameplate().style.display = speaker ? 'flex' : 'none';
  D.ctc().style.display = 'none';
  D.choices().innerHTML = '';
  D.choices().style.display = 'none';

  typeText(D.dialogueText(), text).then(() => {
    D.ctc().style.display = 'block';
    showSceneChoices(scene);
    if (autoMode) startAuto();
  });
}

function showNvlDialogue(text, speaker, mood, scene) {
  showOverlay('nvl');
  const linesEl = D.nvlLines();
  const line = document.createElement('div');
  line.className = 'nvl-line';
  let targetEl = line;
  if (speaker) {
    const s = document.createElement('span');
    s.className = 'nvl-speaker';
    s.style.color = ROUTE_META[scene?.route]?.color || '#ffbf46';
    s.textContent = speaker + ' ';
    line.appendChild(s);
    const t = document.createElement('span');
    line.appendChild(t);
    targetEl = t;
  }
  linesEl.appendChild(line);
  linesEl.scrollTop = linesEl.scrollHeight;
  D.nvlCtc().style.display = 'none';
  D.nvlChoices().innerHTML = '';
  D.nvlChoices().style.display = 'none';

  typeText(targetEl, text).then(() => {
    D.nvlCtc().style.display = 'block';
    showNvlChoices(scene);
    if (autoMode) startAuto();
  });
}

function finishAdvance(visual, scene) {
  D.ctc().style.display = 'block';
  D.dialogueText().textContent = '_';
  D.nvlCtc().style.display = 'block';
  isWaiting = true;
  showSceneChoices(scene);
  if (autoMode) startAuto();
}

function showSceneChoices(scene) {
  if (!scene || !scene.choiceSet || !gameData?.choiceSets) return;
  const choicesData = gameData.choiceSets[scene.category] || gameData.choiceSets.default || [];
  const choicesEl = D.choices();
  choicesEl.innerHTML = '';
  
  for (const ch of choicesData) {
    const btn = document.createElement('button');
    btn.textContent = ch.label;
    btn.title = choiceHint(ch.id, scene.category);
    btn.addEventListener('click', () => {
      skipTyping();
      D.ctc().style.display = 'none';
      D.choices().style.display = 'none';
      advance({ action: 'advance', choice: ch.id });
    });
    choicesEl.appendChild(btn);
  }
  choicesEl.style.display = 'flex';
}

function showNvlChoices(scene) {
  if (!scene || !scene.choiceSet || !gameData?.choiceSets) return;
  const choicesData = gameData.choiceSets[scene.category] || gameData.choiceSets.default || [];
  const el = D.nvlChoices();
  el.innerHTML = '';
  for (const ch of choicesData) {
    const btn = document.createElement('button');
    btn.textContent = ch.label;
    btn.title = choiceHint(ch.id, scene.category);
    btn.addEventListener('click', () => {
      skipTyping();
      D.nvlCtc().style.display = 'none';
      el.style.display = 'none';
      advance({ action: 'advance', choice: ch.id });
    });
    el.appendChild(btn);
  }
  el.style.display = 'flex';
}

function choiceHint(id, category) {
  const hints = {
    sincere: 'ehrlich: Vertrauen und Waerme', careful: 'vorsichtig: Vertrauen/Freundschaft', bold: 'klar: Bindung und Lock-Druck',
    stay: 'Krise: bleiben senkt Repair-Druck', gentle: 'Krise: leise fragen', space: 'Krise: Abstand ohne Abhauen',
    apologize: 'Repair: beste Wahl fuer Vertrauen', explain: 'Repair: Tiefe', action: 'Repair: zeigen statt reden',
    compliment: 'Date: Waerme/Romance', question: 'Date: Tiefe/Secret', silence: 'Date: ruhige Naehe',
    approach: 'Threshold: Romance', wait: 'Threshold: Geduld', promise: 'Threshold: Lock und Secret',
    confess: 'Romance: Bindung', protect: 'Romance: Vertrauen', choose: 'Romance: starker Lock',
    steady: 'Friendship: stabil', light: 'Friendship: leicht', trust: 'Friendship: Vertrauen',
  };
  return hints[id] || `${category}: feste Spielwirkung`;
}

/* ═══════════════════════════════════════
   FREE TEXT
   ═══════════════════════════════════════ */
if (D.talkForm()) {
  D.talkForm().addEventListener('submit', e => {
    e.preventDefault();
    const msg = D.freeMessage().value.trim();
    if (!msg) return;
    D.freeMessage().value = '';
    skipTyping();
    advance({ action: 'talk', message: msg });
  });
}

/* ═══════════════════════════════════════
   ADVANCER (Click / Space / Enter)
   ═══════════════════════════════════════ */
let advancerActive = false;
function setupAdvancer() {
  if (advancerActive) return;
  advancerActive = true;
  document.addEventListener('click', onAdvancer);
  document.addEventListener('keydown', onAdvancerKey);
}
function resetAdvancer() {
  isWaiting = true;
}
function onAdvancer(e) {
  if (e.target.closest('.qm-btn, .menu-btn, .route-pill, .choices button, .close-overlay, .overlay-action-btn, .gtab, .save-slot, #save-server-btn, #save-screenshot-btn, dialog button, .talk-form button, .talk-form textarea, #setup-form *, #restore-form *')) return;
  if (e.target.closest('.overlay-box, dialog')) return;
  if (hideUI) return;
  handleAdvanceInput();
}
function onAdvancerKey(e) {
  if (e.key === ' ' || e.key === 'Enter') {
    if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
    e.preventDefault();
    handleAdvanceInput();
  }
}
function handleAdvanceInput() {
  if (isTyping) { skipTyping(); return; }
  if (isWaiting) {
    if (D.choices().style.display !== 'none' && D.choices().children.length > 0) return;
    advance();
  }
}

/* ═══════════════════════════════════════
   AUTO MODE
   ═══════════════════════════════════════ */
function startAuto() {
  stopAuto();
  const speed = settings?.autoSpeed || 3000;
  autoTimer = setTimeout(() => {
    if (isWaiting) {
      if (D.choices().style.display !== 'none' && D.choices().children.length > 0) return;
      advance();
    }
  }, speed);
}
function stopAuto() {
  if (autoTimer) { clearTimeout(autoTimer); autoTimer = null; }
}
function toggleAuto() {
  autoMode = !autoMode;
  if (autoMode) { if (isWaiting) startAuto(); }
  else stopAuto();
  updateQmButtons();
}

/* ═══════════════════════════════════════
   SKIP MODE
   ═══════════════════════════════════════ */
function toggleSkip() {
  skipMode = !skipMode;
  if (skipMode) {
    skipTyping();
    if (!advanceLock) advance();
  }
  updateQmButtons();
}

/* ═══════════════════════════════════════
   UI UPDATES
   ═══════════════════════════════════════ */
function updateUI() {
  if (!state) return;
  const day = state.day || 1;
  const period = PERIODS[state.periodIndex || 0] || 'Morgen';
  D.dayDisplay().textContent = `Tag ${day} / 30`;
  D.periodDisplay().textContent = period;
  D.calendarTag().classList.remove('hidden');

  if (state.lockedRoute) {
    D.lockDisplay().textContent = `Route: ${ROUTE_META[state.lockedRoute]?.name || state.lockedRoute}`;
  } else {
    D.lockDisplay().textContent = 'Keine Route gelockt';
  }

  D.locationFit().textContent = '';
  D.locationFit().className = 'fit-badge';

  const route = state.currentRoute || 'aurora';
  const meta = ROUTE_META[route];
  D.routePhase().textContent = meta?.name || route;

  renderRouteGuide(lastRouteGuide && lastRouteGuide.route === route ? lastRouteGuide : buildLocalRouteGuide(route));
  updateRoutePills();
}

function updateRoutePills() {
  $$('.route-pill').forEach(p => {
    const r = p.dataset.route;
    p.classList.toggle('active', r === (state?.currentRoute || 'aurora'));
    const lockedOut = Boolean(state?.lockedRoute && r && r !== state.lockedRoute && p.closest('#route-select-bar'));
    p.classList.toggle('locked-out', lockedOut);
    if (lockedOut) p.title = 'Route ist gelockt. Andere Routen kannst du im Status ansehen.';
  });
}

function updateCharacter(route, visual, location) {
  const meta = ROUTE_META[route || state?.currentRoute];
  if (meta) {
    D.speakerName().textContent = meta.name;
    D.nameplate().style.background = meta.color;
  }
  if (location && gameData?.locations?.[location]) {
    D.locationName().textContent = gameData.locations[location].name || location;
    D.locationFit().textContent = '';
  }
  if (visual) {
    D.speakerMood().textContent = visual;
  }
  loadCharacterModel(route || state?.currentRoute || 'aurora');
  setCharacterVisual(visual);
}

function buildLocalRouteGuide(route) {
  const rel = state?.relationships?.[route] || {};
  const pressures = state?.routePressure?.[route] || {};
  const locked = state?.lockedRoute === route;
  const name = ROUTE_META[route]?.name || route;
  let nextGoal = 'Baue Bindung auf und plane ein Rendezvous.';
  if (locked) nextGoal = 'Route gelockt: Halte Bindung hoch und repariere offene Krisen fuer True/Secret.';
  else if ((state?.flags || []).includes(`route_lock_ready_${route}`)) nextGoal = 'Route-Lock bereit: waehle jetzt bewusst eine romantische Antwort wie Wählen oder Andeuten.';
  else if ((rel.bond || 0) >= 45 && (state?.commitmentScore?.[route] || 0) >= 5) nextGoal = 'Route-Lock bereit: waehle klare romantische Antworten.';
  else if ((pressures.needs_repair || 0) >= 4) nextGoal = 'Offene Krise: Entschuldigen, helfen oder konkret reparieren.';
  if ((state?.day || 1) === 30 && (state?.periodIndex || 0) < 3) nextGoal = 'Finale heute Nacht: nutze den Tag nur noch fuer letzte Vorbereitung und Ruhe.';
  const warnings = [];
  if ((pressures.needs_repair || 0) >= 4) warnings.push('Krise offen');
  if ((rel.bomb || 0) >= 6) warnings.push('Bombe tickt');
  if ((rel.jealousy || 0) >= 6) warnings.push('Eifersucht');
  if ((rel.neglect || 0) >= 6) warnings.push('Funkstille');
  if ((state?.playerStats?.fatigue || 0) >= 120) warnings.push('Fatigue hoch');
  if ((state?.day || 1) >= 13 && !state?.lockedRoute) warnings.push('Route bald locken');
  return { route, name, stage: locked ? 'Route gelockt' : (rel.dates ? 'Kennenlernen' : 'Anfang'), nextGoal, warnings, pressures };
}

function renderRouteGuide(guide) {
  if (!guide || !D.guideCard()) return;
  D.guideCard().classList.remove('hidden');
  D.guideStage().textContent = `${guide.name || ROUTE_META[guide.route]?.name || 'Route'} · ${guide.stage || 'Anfang'}`;
  const warning = guide.warnings?.length ? ` Achtung: ${guide.warnings[0]}` : '';
  const missing = guide.lockStatus?.missing?.length ? ` Fehlt: ${guide.lockStatus.missing.slice(0, 2).join(', ')}.` : '';
  const finalNote = (state?.day === 30 && (state?.periodIndex || 0) < 3) ? ' Finale erst heute Nacht.' : '';
  D.guideGoal().textContent = `${guide.nextGoal || 'Baue Bindung auf.'}${missing}${warning}${finalNote}`;
}

function renderActionFeedback(feedback) {
  const el = D.actionFeedback();
  if (!el) return;
  if (!feedback) {
    el.classList.add('hidden');
    el.innerHTML = '';
    return;
  }
  const chips = [];
  for (const h of feedback.highlights || []) {
    if (!h.delta) continue;
    const sign = h.delta > 0 ? '+' : '';
    chips.push(`<span class="feedback-chip ${h.delta < 0 ? 'negative' : ''}">${escapeHtml(h.label)} ${sign}${h.delta}</span>`);
  }
  const rawMessages = feedback.messages || [];
  const routeLockMessages = rawMessages.filter(m => String(m).toLowerCase().includes('route gelockt'));
  const otherMessages = rawMessages.filter(m => !routeLockMessages.includes(m));
  const messages = [...routeLockMessages, ...otherMessages].slice(0, 5).map(m => `<div class="feedback-message">${escapeHtml(m)}</div>`).join('');
  const warnings = (feedback.warnings || []).slice(0, 2).map(w => `<div class="feedback-warning">${escapeHtml(w)}</div>`).join('');
  el.innerHTML = `
    <div class="feedback-title">Auswirkung</div>
    <div class="feedback-chips">${chips.join('') || '<span class="feedback-chip">Keine Werte geaendert</span>'}</div>
    ${messages}${warnings}
  `;
  el.classList.remove('hidden');
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* ═══════════════════════════════════════
   NVL TOGGLE
   ═══════════════════════════════════════ */
function getEffectiveNvlMode(scene) {
  const pref = settings?.nvlMode || 'auto';
  if (pref === 'adv') return 'adv';
  if (pref === 'nvl') return 'nvl';
  if (!scene) return 'adv';
  const cat = scene.category;
  if (['finale', 'secret', 'intro'].includes(cat)) return 'nvl';
  if (cat === 'romance' && scene.chapter?.includes('Confession')) return 'nvl';
  return 'adv';
}

/* ═══════════════════════════════════════
   QUICK MENU
   ═══════════════════════════════════════ */
document.addEventListener('click', e => {
  const btn = e.target.closest('.qm-btn');
  if (!btn) return;
  const action = btn.dataset.action;
  switch (action) {
    case 'skip': toggleSkip(); break;
    case 'auto': toggleAuto(); break;
    case 'backlog': openBacklog(); break;
    case 'save': openSaveLoad(); break;
    case 'schedule': openSchedule(); break;
    case 'date': openDate(); break;
    case 'status': openStatus(); break;
    case 'settings': openSettings(); break;
    case 'nvl-toggle': toggleNvlMode(); break;
    case 'hide': toggleHide(); break;
  }
});

function updateQmButtons() {
  $$('.qm-btn[data-action="auto"]').forEach(b => b.classList.toggle('active', autoMode));
  $$('.qm-btn[data-action="skip"]').forEach(b => b.classList.toggle('active', skipMode));
}

function toggleNvlMode() {
  const cur = settings?.nvlMode || 'auto';
  const next = cur === 'adv' ? 'nvl' : cur === 'nvl' ? 'auto' : 'adv';
  if (settings) settings.nvlMode = next;
  if (state?.settings) state.settings.nvlMode = next;
  saveSettingsToState();
}

function toggleHide() {
  hideUI = !hideUI;
  document.body.classList.toggle('hide-ui', hideUI);
}

/* ═══════════════════════════════════════
   ROUTE SELECT
   ═══════════════════════════════════════ */
document.addEventListener('click', e => {
  const pill = e.target.closest('.route-pill');
  if (!pill || !state) return;
  if (!pill.closest('#route-select-bar')) return;
  const route = pill.dataset.route;
  if (state.lockedRoute && route !== state.lockedRoute) return;
  if (state.currentRoute === route) return;
  state.currentRoute = route;
  updateUI();
  updateCharacter(route, null, null);
  const nvlEl = D.screen('nvl');
  if (!nvlEl.classList.contains('hidden')) {
    D.nvlLines().innerHTML = '';
  }
});

/* ═══════════════════════════════════════
   CLOSE OVERLAYS
   ═══════════════════════════════════════ */
document.addEventListener('click', e => {
  const close = e.target.closest('[data-close]');
  if (!close) return;
  const overlay = close.closest('.overlay-screen');
  if (overlay) overlay.classList.add('hidden');
});

/* ═══════════════════════════════════════
   SCHEDULE
   ═══════════════════════════════════════ */
async function openSchedule() {
  if (!state || !gameData) return;
  showOverlay('schedule');
  const day = state.day || 1;
  const period = PERIODS[state.periodIndex || 0];
  D.screen('schedule').querySelector('#schedule-day').textContent = `Tag ${day} · ${period}`;

  const fatigue = state.playerStats?.fatigue || 0;
  const currency = state.currency || 0;
  $('#schedule-fatigue').textContent = fatigue;
  $('#schedule-currency').textContent = currency;

  const neglect = state.relationships?.[state.currentRoute]?.neglect || 0;
  const guide = lastRouteGuide?.route === state.currentRoute ? lastRouteGuide : buildLocalRouteGuide(state.currentRoute || 'aurora');
  $('#schedule-guide').textContent = `${guide.nextGoal || 'Plane deine Zeit.'} ${scheduleHint(day)} ${specialDayHint(day)} Training hilft bei Szenen-Gates; Dates steigern Bindung direkt.`;

  const social = state?.rumors?.filter(r => !r.resolved && (r.expiresDay || 99) >= day) || [];
  const warn = $('#neglect-warning');
  const warnings = guide.warnings || [];
  const specials = Object.keys(getCurrentSpecialDays());
  if (social.length || specials.length || neglect >= 7 || warnings.length) {
    const parts = [];
    if (specials.length) parts.push(`⭐ Heute: ${specials.map(s => gameData?.specialDays?.[s]?.label || s).join(', ')}.`);
    if (social.length) parts.push(`🗣 ${social.length} Geruecht(e) aktiv: "${social[0].text?.slice(0, 60)}".`);
    warn.classList.remove('hidden');
    warn.textContent = parts.concat(warnings[0] || '').filter(Boolean).join(' ');
  } else {
    warn.classList.add('hidden');
  }

  renderCalendarBar(day);
  renderScheduleGrid(fatigue, currency);
}

function renderCalendarBar(currentDay) {
  const bar = $('#calendar-bar');
  bar.innerHTML = '';
  for (let d = 1; d <= 30; d++) {
    const el = document.createElement('div');
    el.className = 'cal-day' + (d === currentDay ? ' today' : '');
    el.innerHTML = `<span class="day-num">${d}</span>`;
    if (gameData?.calendar) {
      const events = gameData.calendar.filter(e => e.day === d && (e.known !== false));
      if (events.length) {
        el.innerHTML += `<span class="day-event" title="${events.map(e => e.label).join(', ')}">✦</span>`;
      }
    }
    bar.appendChild(el);
  }
  bar.scrollLeft = Math.max(0, (currentDay - 3) * 38);
}

function scheduleHint(day) {
  const nextEvent = nextKnownEvent(day);
  const shop = isShopOpen() ? 'Der Teilehaendler ist heute da.' : 'Shop-Tage: 4, 7, 15, 21, 27.';
  const finale = day === 30 ? 'Heute entscheidet die Nacht.' : '';
  return [nextEvent ? `Naechstes Ereignis: Tag ${nextEvent.day} ${nextEvent.period} - ${nextEvent.label}.` : '', shop, finale].filter(Boolean).join(' ');
}

function specialDayHint(day) {
  if (!gameData?.specialDays) return '';
  const upcoming = Object.entries(gameData.specialDays)
    .filter(([_, s]) => s.day >= day && s.day <= day + 3)
    .map(([id, s]) => `${s.label} (Tag ${s.day})`);
  return upcoming.length ? `📅 Demnaechst: ${upcoming.join(', ')}. ` : '';
}

function nextKnownEvent(day) {
  return (gameData?.calendar || [])
    .filter(e => e.known !== false && e.day >= day)
    .sort((a, b) => a.day - b.day || PERIODS.indexOf(a.period) - PERIODS.indexOf(b.period))[0];
}

function renderScheduleGrid(fatigue, currency) {
  const grid = $('#schedule-grid');
  grid.innerHTML = '';
  const actions = gameData?.scheduleActions || {};
  for (const [id, act] of Object.entries(actions)) {
    const card = document.createElement('button');
    card.className = 'schedule-card';
    const disabled = act.fatigue > 0 && fatigue + act.fatigue > 150;
    card.disabled = disabled;
    const iconMap = { work: '⚙', study: '📘', courage: '💪', scrap: '🔧', rest: '💤', charm: '✨', focus: '🎯' };
    card.innerHTML = `
      <span class="sc-icon">${iconMap[id] || '📋'}</span>
      <span class="sc-label">${act.label || id}</span>
      <span class="sc-effects">${act.currency ? `+${act.currency}¢ ` : ''}${act.fatigue < 0 ? `-${Math.abs(act.fatigue)} Fatigue` : act.fatigue > 0 ? `+${act.fatigue} Fatigue` : ''} ${act.stats ? Object.entries(act.stats).map(([k, v]) => `${k} +${v}`).join(' ') : ''}</span>
    `;
    card.addEventListener('click', () => doScheduleActivity(id));
    grid.appendChild(card);
  }
  renderSocialCards(grid, fatigue);
  renderShopCards(grid, currency);
}

function renderSocialCards(grid, fatigue) {
  if (!gameData?.socialActors) return;
  const actors = gameData.socialActors;
  for (const [id, actor] of Object.entries(actors)) {
    const link = state?.socialLinks?.[id] || {};
    const mood = link.mood || 'neutral';
    const card = document.createElement('button');
    card.className = 'schedule-card social-card';
    card.disabled = fatigue >= 140;
    card.innerHTML = `
      <span class="sc-icon">🗣</span>
      <span class="sc-label">${actor.name}</span>
      <span class="sc-effects">${actor.role} · Bindung: ${link.bond || 0}</span>
    `;
    card.addEventListener('click', () => doSocialVisit(id));
    grid.appendChild(card);
  }
  const activeRumors = state?.rumors?.filter(r => !r.resolved && (r.expiresDay || 99) >= (state?.day || 1)) || [];
  if (activeRumors.length) {
    const repairCard = document.createElement('button');
    repairCard.className = 'schedule-card social-card';
    repairCard.innerHTML = `
      <span class="sc-icon">🔧</span>
      <span class="sc-label">Geruecht klaeren</span>
      <span class="sc-effects">${activeRumors.length} aktiv · ${activeRumors[0].text?.slice(0, 50)}</span>
    `;
    repairCard.addEventListener('click', () => doRepairRumor());
    grid.appendChild(repairCard);
  }
  const specialsToday = getCurrentSpecialDays();
  for (const [sid, special] of Object.entries(specialsToday)) {
    const attendCard = document.createElement('button');
    attendCard.className = 'schedule-card special-card';
    attendCard.innerHTML = `
      <span class="sc-icon">⭐</span>
      <span class="sc-label">${special.label}</span>
      <span class="sc-effects">Spezialtag · Geschenk gibt Bonus</span>
    `;
    attendCard.addEventListener('click', () => doAttendSpecialDay(sid));
    grid.appendChild(attendCard);
  }
}

function getCurrentSpecialDays() {
  if (!gameData?.specialDays || !state) return {};
  return Object.fromEntries(
    Object.entries(gameData.specialDays).filter(([_, s]) => s.day === state.day)
  );
}

async function doSocialVisit(actor) {
  hideOverlay('schedule');
  skipTyping();
  await advance({ action: 'social_visit', actor });
}

async function doRepairRumor() {
  hideOverlay('schedule');
  skipTyping();
  await advance({ action: 'repair_rumor', actor: 'sigi', rumorId: '' });
}

async function doAttendSpecialDay(specialDay) {
  hideOverlay('schedule');
  skipTyping();
  await advance({ action: 'attend_special_day', specialDay });
}

function renderShopCards(grid, currency) {
  if (!isShopOpen()) return;
  const items = gameData?.items || {};
  for (const [id, item] of Object.entries(items)) {
    if (item.source !== 'shop') continue;
    const card = document.createElement('button');
    card.className = 'schedule-card';
    card.disabled = currency < item.cost;
    card.innerHTML = `
      <span class="sc-icon">▣</span>
      <span class="sc-label">${item.name}</span>
      <span class="sc-effects">${item.cost} Schraubmarken · liegt beim Teilehändler</span>
    `;
    card.addEventListener('click', () => buyShopItem(id));
    grid.appendChild(card);
  }
}

function isShopOpen() {
  const day = state?.day || 1;
  if ([4, 7, 15, 21, 27].includes(day)) return true;
  return (state?.eventsSeen || []).some(id => ['scrap_market_4', 'parts_delivery_7', 'last_gift_27'].includes(id));
}

async function doScheduleActivity(activity) {
  hideOverlay('schedule');
  skipTyping();
  await advance({ action: 'schedule', activity });
}

async function buyShopItem(itemId) {
  hideOverlay('schedule');
  skipTyping();
  await advance({ action: 'buy', itemId });
}

/* ═══════════════════════════════════════
   DATE
   ═══════════════════════════════════════ */
async function openDate() {
  if (!state || !gameData) return;
  showOverlay('date');
  const route = state.lockedRoute || state.currentRoute || 'aurora';
  updateDateGuide(route);
  updateDateRoutePills(route);
  populateDateLocations(route);
  populateDateGifts(route);
}

function updateDateGuide(route) {
  const el = $('#date-guide');
  if (!el) return;
  const guide = lastRouteGuide?.route === route ? lastRouteGuide : buildLocalRouteGuide(route);
  const lockText = state?.lockedRoute
    ? `Route gelockt: Rendezvous zaehlen nur noch fuer ${ROUTE_META[state.lockedRoute]?.name || state.lockedRoute}.`
    : 'Ein Rendezvous kostet Zeit und ist auf ein Date pro Bagger/Tag begrenzt. Ort, Uhrzeit, Fatigue und Geschenk entscheiden den Ausgang.';
  el.textContent = `${guide.name || ROUTE_META[route]?.name || route}: ${guide.nextGoal || 'Passenden Ort waehlen.'} ${lockText}`;
}

function updateDateRoutePills(active) {
  const container = D.screen('date')?.querySelector('#date-route-select');
  if (!container) return;
  container.querySelectorAll('.route-pill').forEach(p => {
    p.classList.toggle('active', p.dataset.route === active);
    const lockedOut = Boolean(state?.lockedRoute && p.dataset.route !== state.lockedRoute);
    p.classList.toggle('locked-out', lockedOut);
    p.disabled = lockedOut;
    p.title = lockedOut ? 'Route ist bereits gelockt.' : '';
  });
}

D.screen('date')?.querySelector('#date-route-select')?.addEventListener('click', e => {
  const pill = e.target.closest('.route-pill');
  if (!pill) return;
  if (state?.lockedRoute && pill.dataset.route !== state.lockedRoute) return;
  updateDateGuide(pill.dataset.route);
  updateDateRoutePills(pill.dataset.route);
  populateDateLocations(pill.dataset.route);
  populateDateGifts(pill.dataset.route);
});

function populateDateLocations(route) {
  const sel = $('#date-location');
  if (!sel || !gameData?.locations) return;
  sel.innerHTML = '';
  for (const [id, loc] of Object.entries(gameData.locations)) {
    if (loc.unlockDay && (state?.day || 1) < loc.unlockDay) continue;
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = loc.name;
    opt.dataset.tags = (loc.tags || []).join(',');
    sel.appendChild(opt);
  }
  sel.dispatchEvent(new Event('change'));
  sel.onchange = () => updateLocationFit(sel, route);
  updateLocationFit(sel, route);
}

function updateLocationFit(sel, route) {
  const locId = sel.value;
  const loc = gameData?.locations?.[locId];
  const bagger = gameData?.baggers?.[route];
  if (!loc || !bagger) {
    $('#location-tags').textContent = '';
    $('#location-fit-display').textContent = '';
    return;
  }
  const tags = loc.tags || [];
  $('#location-tags').textContent = tags.join(' · ');
  const fitEl = $('#location-fit-display');
  const fit = computeLocationFit(route, tags);
  fitEl.textContent = `${fitLabel(fit)} · ${locationHint(tags)}`;
  fitEl.className = `location-fit-text fit-${fit === 'good' ? 'good' : fit === 'poor' ? 'poor' : 'neutral'}`;

  const riskEl = $('#date-social-risk');
  if (tags.includes('public') || tags.includes('crowded')) {
    const rumorCount = (state?.rumors || []).filter(r => !r.resolved).length;
    riskEl.textContent = `⚠ Oeffentlich — Zeugen moeglich${rumorCount ? ` (${rumorCount} Geruecht(e) aktiv!)` : ''}.`;
    riskEl.className = 'social-risk-text risky';
  } else {
    riskEl.textContent = '✅ Privater Ort — kein Risiko fuer Gerede.';
    riskEl.className = 'social-risk-text safe';
  }
}

function computeLocationFit(route, tags) {
  const bagger = gameData?.baggers?.[route] || {};
  const preferred = new Set(bagger.preferredTags || []);
  const disliked = new Set(bagger.dislikedTags || []);
  const liked = tags.filter(t => preferred.has(t)).length;
  const bad = tags.filter(t => disliked.has(t)).length;
  if (liked >= 2 && bad <= 1) return 'good';
  if (bad && liked === 0) return 'poor';
  return 'neutral';
}

function fitLabel(fit) {
  if (fit === 'good') return 'Passt gut';
  if (fit === 'poor') return 'Riskant';
  if (fit === 'critical') return 'Schluesselgeschenk';
  if (fit === 'liked') return 'Mag diese Route';
  if (fit === 'disliked') return 'Schlechte Wahl';
  return 'Neutral';
}

function locationHint(tags) {
  if (tags.includes('quiet')) return 'Es ist still genug, dass man die Hydraulik arbeiten hört.';
  if (tags.includes('loud')) return 'Vom Platz kommt Lärm rüber. Man muss lauter reden als sonst.';
  if (tags.includes('technical')) return 'Werkzeug liegt griffbereit. Irgendwas braucht immer Wartung.';
  if (tags.includes('memory')) return 'Der Ort wirkt, als hätte hier schon mal jemand zu lange gewartet.';
  return 'Ein Ort wie jeder andere, bis jemand dort etwas sagt.';
}

function populateDateGifts(route) {
  const sel = $('#gift-item-select');
  if (!sel) return;
  sel.innerHTML = '<option value="">Kein Geschenk</option>';
  const inv = state?.inventory || {};
  for (const [id, item] of Object.entries(gameData?.items || {})) {
    if (inv[id] && inv[id] > 0) {
      const opt = document.createElement('option');
      opt.value = id;
      opt.textContent = `${item.name} (×${inv[id]})`;
      sel.appendChild(opt);
    }
  }
  sel.onchange = () => updateGiftFit(sel, route);
  updateGiftFit(sel, route);
}

function updateGiftFit(sel, route) {
  const fitEl = $('#gift-fit-display');
  if (!sel.value) {
    fitEl.textContent = '';
    return;
  }
  const fit = computeGiftFit(route, sel.value);
  const item = gameData?.items?.[sel.value];
  const tags = item?.tags || [];
  fitEl.textContent = `${fitLabel(fit)} · ${tags.join(' · ')}`;
  fitEl.className = `gift-fit-text fit-${fit === 'critical' || fit === 'liked' ? 'good' : fit === 'disliked' ? 'poor' : 'neutral'}`;
}

function computeGiftFit(route, itemId) {
  const prefs = gameData?.giftPreferences?.[route] || {};
  if (itemId === prefs.critical) return 'critical';
  if ((prefs.liked || []).includes(itemId)) return 'liked';
  if ((prefs.disliked || []).includes(itemId)) return 'disliked';
  return 'neutral';
}

$('#date-start')?.addEventListener('click', async () => {
  const route = D.screen('date')?.querySelector('.route-pill.active')?.dataset.route || state?.currentRoute || 'aurora';
  const location = $('#date-location')?.value;
  if (!location) return;
  const gift = $('#gift-item-select')?.value || '';
  hideOverlay('date');
  skipTyping();
  await advance({ action: 'start_date', route, location, gift });
});

$('#date-invite')?.addEventListener('click', async () => {
  const route = D.screen('date')?.querySelector('.route-pill.active')?.dataset.route || state?.currentRoute || 'aurora';
  const location = $('#date-location')?.value;
  if (!location) return;
  const gift = $('#gift-item-select')?.value || '';
  hideOverlay('date');
  skipTyping();
  await advance({ action: 'invite_date', route, location, gift });
});

/* ═══════════════════════════════════════
   STATUS
   ═══════════════════════════════════════ */
function openStatus() {
  if (!state) return;
  showOverlay('status');
  const route = state.currentRoute || 'aurora';
  updateStatusRoutePills(route);
  populateStatus(route);
}

function updateStatusRoutePills(active) {
  const container = D.screen('status')?.querySelector('#status-route-select');
  if (!container) return;
  container.querySelectorAll('.route-pill').forEach(p => {
    p.classList.toggle('active', p.dataset.route === active);
  });
}

D.screen('status')?.querySelector('#status-route-select')?.addEventListener('click', e => {
  const pill = e.target.closest('.route-pill');
  if (!pill) return;
  updateStatusRoutePills(pill.dataset.route);
  populateStatus(pill.dataset.route);
});

function populateStatus(route) {
  const rel = state?.relationships?.[route];
  if (!rel) return;
  const meta = ROUTE_META[route];
  const guide = lastRouteGuide?.route === route ? lastRouteGuide : buildLocalRouteGuide(route);

  $('#status-route-name').textContent = gameData?.baggers?.[route]?.routeWord || `${meta?.name}-Route`;
  $('#s-next-goal').textContent = guide.nextGoal || 'Baue Bindung auf und plane Dates.';
  $('#s-advice').textContent = guide.advice || routeAdvice(route);
  $('#s-avoid').textContent = guide.avoid ? `Vermeiden: ${guide.avoid}` : '';
  const warnings = guide.warnings || [];
  $('#s-warnings').innerHTML = warnings.length
    ? warnings.map(w => `<span class="status-warning">${escapeHtml(w)}</span>`).join('')
    : '<span class="rm-node visited">Keine akute Warnung</span>';

  const bond = rel.bond || 0;
  $('#s-bond').textContent = `${bond}%`;
  $('#s-bond-bar').style.width = `${bond}%`;
  $('#s-trust').textContent = rel.trust || 0;
  $('#s-warmth').textContent = rel.warmth || 0;
  $('#s-depth').textContent = rel.depth || 0;
  $('#s-courage').textContent = rel.courage || 0;
  $('#s-dates').textContent = rel.dates || 0;
  $('#s-commitment').textContent = state.commitmentScore?.[route] || 0;

  const sEl = $('#s-player-stats');
  const stats = state.playerStats || {};
  sEl.innerHTML = Object.entries(stats).map(([k, v]) =>
    `<div class="stat-row"><span>${k}</span><strong>${v}</strong></div>`
  ).join('');
  $('#s-currency').textContent = state.currency || 0;

  const mapEl = $('#route-map');
  if (gameData?.routes?.[route]) {
    const routeData = gameData.routes[route];
    mapEl.innerHTML = routeData.map(n => {
      const visited = state.flags?.some(f => n.setsFlags?.includes(f));
      const secret = n.category === 'secret';
      const finale = n.category === 'finale';
      const cls = (visited ? 'visited' : '') + (secret ? ' secret' : '') + (finale ? ' finale' : '');
      const label = visited ? (n.chapter || n.id) : '???';
      return `<span class="rm-node ${cls}">${label}</span>`;
    }).join('');
  }

  const pressureEl = $('#s-pressure');
  const pressures = state.routePressure?.[route] || {};
  const pressureLabels = {
    toward_romance: 'Romance', toward_friendship: 'Freundschaft', needs_repair: 'Repair-Druck',
    opens_secret: 'Secret-Spur', toward_crisis: 'Krise', toward_lockin: 'Lock-Druck'
  };
  const pressureRows = Object.entries(pressureLabels).map(([key, label]) =>
    `<div class="pressure-row"><span>${label}</span><strong>${pressures[key] || 0}</strong></div>`
  );
  pressureRows.push(`<div class="pressure-row"><span>Funkstille</span><strong>${rel.neglect || 0}</strong></div>`);
  pressureRows.push(`<div class="pressure-row"><span>Eifersucht</span><strong>${rel.jealousy || 0}</strong></div>`);
  pressureRows.push(`<div class="pressure-row"><span>Bombe</span><strong>${rel.bomb || 0}</strong></div>`);
  pressureEl.innerHTML = pressureRows.join('');

  const memEl = $('#s-memories');
  memEl.innerHTML = '';
  if (rel.memories && rel.memories.length) {
    rel.memories.slice(-12).forEach(m => {
      const li = document.createElement('li');
      li.textContent = m;
      memEl.appendChild(li);
    });
  } else {
    memEl.innerHTML = '<li class="fit-neutral">Noch keine Erinnerungen</li>';
  }

  const promEl = $('#s-promises');
  if (state.promises && state.promises.length) {
    promEl.innerHTML = state.promises.filter(p => !p.broken).map(p =>
      `<span class="rm-node ${p.kept ? 'visited' : ''}">${p.label || p.id}</span>`
    ).join('');
  } else {
    promEl.innerHTML = '';
  }
  populateSocialStatus(route);
}

function populateSocialStatus(route) {
  const rep = state?.reputation || {};
  const repEl = $('#s-reputation');
  if (repEl) {
    repEl.innerHTML = Object.entries(rep).map(([k, v]) => {
      const cls = v > 5 ? 'positive' : v < -5 ? 'negative' : '';
      return `<span class="rep-entry ${cls}">${escapeHtml(k)}: ${v > 0 ? '+' : ''}${v}</span>`;
    }).join('');
  }
  const links = state?.socialLinks || {};
  const linkEl = $('#s-social-links');
  if (linkEl) {
    linkEl.innerHTML = Object.entries(links).map(([id, link]) => {
      const name = gameData?.socialActors?.[id]?.name || id;
      return `<div class="social-actor"><span>${escapeHtml(name)}</span><strong>Bindung ${link.bond || 0} · Vertrauen ${link.trust || 0}</strong></div>`;
    }).join('');
  }
  const rumors = (state?.rumors || []).filter(r => !r.resolved && (r.expiresDay || 99) >= (state?.day || 1));
  const rumorEl = $('#s-rumors');
  if (rumorEl) {
    rumorEl.innerHTML = rumors.length
      ? rumors.map(r => `<div class="rumor-entry"><strong>${escapeHtml(r.source || '?')}</strong>: ${escapeHtml(r.text?.slice(0, 80))}</div>`).join('')
      : '<span class="fit-neutral">Keine aktiven Gerüchte</span>';
  }
  const prefs = state?.knownPreferences || [];
  const prefEl = $('#s-known-prefs');
  if (prefEl) {
    prefEl.innerHTML = prefs.length
      ? prefs.map(p => {
        const item = gameData?.items?.[p];
        return `<span class="rm-node visited">${escapeHtml(item?.name || p)}</span>`;
      }).join('')
      : '<span class="fit-neutral">Noch keine Vorlieben bekannt</span>';
  }
}

function routeAdvice(route) {
  const bagger = gameData?.baggers?.[route] || {};
  const preferred = (bagger.preferredTags || []).join(', ');
  const gifts = (gameData?.giftPreferences?.[route]?.liked || []).map(id => gameData?.items?.[id]?.name || id).join(', ');
  return `Gute Tags: ${preferred || 'ruhig, passend'} · Gute Geschenke: ${gifts || 'kleine passende Dinge'}`;
}

/* ═══════════════════════════════════════
   SETTINGS
   ═══════════════════════════════════════ */
function getDefaultSettings() {
  return { textSpeed: 35, autoSpeed: 3000, skipMode: 'read', nvlMode: 'auto', showFreeText: true };
}

function loadSettingsFromStorage() {
  try {
    const saved = localStorage.getItem('bagger_settings');
    if (saved) {
      const parsed = JSON.parse(saved);
      settings = { ...getDefaultSettings(), ...parsed };
    } else {
      settings = getDefaultSettings();
    }
  } catch {
    settings = getDefaultSettings();
  }
}

function saveSettingsToStorage() {
  try { localStorage.setItem('bagger_settings', JSON.stringify(settings)); } catch {}
}

function saveSettingsToState() {
  if (state?.settings) Object.assign(state.settings, settings);
  saveSettingsToStorage();
}

function applySettings() {
  if (state?.settings) settings = { ...getDefaultSettings(), ...state.settings };
  else loadSettingsFromStorage();
  D.freeTextArea()?.classList.toggle('hidden', settings.showFreeText === false);
}

function openSettings() {
  showOverlay('settings');
  if (!settings) loadSettingsFromStorage();
  $('#set-text-speed').value = settings.textSpeed;
  $('#set-text-label').textContent = settings.textSpeed > 60 ? 'schnell' : settings.textSpeed > 35 ? 'mittel' : 'langsam';
  $('#set-auto-speed').value = settings.autoSpeed;
  $('#set-auto-label').textContent = `${settings.autoSpeed / 1000}s`;
  if ($('#set-skip-mode')) $('#set-skip-mode').value = settings.skipMode || 'read';
  $('#set-nvl-mode').value = settings.nvlMode || 'auto';
  $('#set-freetext').checked = settings.showFreeText !== false;
}

$('#set-text-speed')?.addEventListener('input', function() {
  settings.textSpeed = +this.value;
  $('#set-text-label').textContent = this.value > 60 ? 'schnell' : this.value > 35 ? 'mittel' : 'langsam';
  saveSettingsToState();
});
$('#set-auto-speed')?.addEventListener('input', function() {
  settings.autoSpeed = +this.value;
  $('#set-auto-label').textContent = `${this.value / 1000}s`;
  saveSettingsToState();
});
$('#set-skip-mode')?.addEventListener('change', function() {
  settings.skipMode = this.value;
  saveSettingsToState();
});
$('#set-nvl-mode')?.addEventListener('change', function() {
  settings.nvlMode = this.value;
  saveSettingsToState();
});
$('#set-freetext')?.addEventListener('change', function() {
  settings.showFreeText = this.checked;
  D.freeTextArea()?.classList.toggle('hidden', settings.showFreeText === false);
  saveSettingsToState();
});

/* ═══════════════════════════════════════
   SAVE / LOAD
   ═══════════════════════════════════════ */
const MAX_SLOTS = 12;

function openSaveLoad() {
  showOverlay('save');
  renderSaveGrid();
  const token = serverSaveToken || localStorage.getItem('bagger_last_token') || '—';
  $('#save-token-display').textContent = token;
}

function getSaveSlots() {
  try { return JSON.parse(localStorage.getItem('bagger_saves') || '[]'); } catch { return []; }
}

function putSaveSlots(slots) {
  try { localStorage.setItem('bagger_saves', JSON.stringify(slots)); } catch {}
}

function renderSaveGrid() {
  const grid = $('#save-grid');
  grid.innerHTML = '';
  const slots = getSaveSlots();
  for (let i = 0; i < MAX_SLOTS; i++) {
    const slot = slots[i];
    const el = document.createElement('div');
    el.className = 'save-slot' + (slot ? ' used' : '');
    if (slot) {
      el.innerHTML = `
        <span class="slot-num">${i + 1}</span>
        <div class="slot-preview">📷</div>
        <div class="slot-info">
          <strong>${slot.label || 'Slot ' + (i + 1)}</strong>
          <span>Tag ${slot.day || '?'} · ${slot.period || ''} · ${slot.route || ''}</span>
        </div>
      `;
      el.addEventListener('click', e => {
        if (e.shiftKey) {
          if (confirm('Slot ' + (i + 1) + ' überschreiben?')) saveToSlot(i);
        } else {
          if (confirm('Slot ' + (i + 1) + ' laden?')) loadFromSlot(i);
        }
      });
    } else {
      el.innerHTML = `<span class="slot-num">${i + 1}</span><span style="color:var(--muted);font-size:0.8rem;margin-top:auto">Leer</span>`;
      el.addEventListener('click', () => saveToSlot(i));
    }
    grid.appendChild(el);
  }
}

async function saveToSlot(index) {
  if (!state) return;
  const slots = getSaveSlots();
  slots[index] = {
    label: `Tag ${state.day} – ${PERIODS[state.periodIndex] || ''}`,
    day: state.day,
    period: PERIODS[state.periodIndex] || '',
    route: state.currentRoute,
    timestamp: Date.now(),
    state: JSON.parse(JSON.stringify(state)),
  };
  putSaveSlots(slots);
  renderSaveGrid();
}

async function loadFromSlot(index) {
  const slots = getSaveSlots();
  const slot = slots[index];
  if (!slot || !slot.state) return;
  state = slot.state;
  settings = state.settings || getDefaultSettings();
  applySettings();
  hideOverlay('save');
  D.nvlLines().innerHTML = '';
  startGameLoop();
  D.dialogueText().textContent = `Spielstand geladen: Tag ${state.day || '?'} · ${PERIODS[state.periodIndex || 0] || ''}.`;
  renderRouteGuide(buildLocalRouteGuide(state.currentRoute || 'aurora'));
  resetAdvancer();
}

$('#save-server-btn')?.addEventListener('click', async () => {
  if (!state) return;
  try {
    const token = serverSaveToken || undefined;
    const data = await apiPost('/save', { state, token });
    if (data.ok && data.token) {
      serverSaveToken = data.token;
      localStorage.setItem('bagger_last_token', serverSaveToken);
      $('#save-token-display').textContent = serverSaveToken;
    }
  } catch (err) { console.error('server save:', err); }
});

$('#save-screenshot-btn')?.addEventListener('click', () => {
  const html = document.documentElement;
  html.requestFullscreen?.();
});

/* ═══════════════════════════════════════
   GALLERY
   ═══════════════════════════════════════ */
let galleryTab = 'endings';

function openGallery() {
  showOverlay('gallery');
  renderGallery();
}

function renderGallery() {
  const content = $('#gallery-content');
  content.innerHTML = '';

  if (galleryTab === 'endings') renderGalleryEndings(content);
  else if (galleryTab === 'memories') renderGalleryMemories(content);
  else if (galleryTab === 'music') renderGalleryMusic(content);
}

function renderGalleryEndings(container) {
  const seenEndings = JSON.parse(localStorage.getItem('bagger_endings') || '[]');
  if (!seenEndings.length) {
    container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px">Noch keine Endings freigespielt.</p>';
    return;
  }
  for (const e of seenEndings) {
    const card = document.createElement('div');
    card.className = 'gal-card';
    const routeName = ROUTE_META[e.route]?.name || e.route;
    const kindLabel = ENDING_KIND_LABELS[e.kind] || e.kind;
    card.innerHTML = `
      <div class="gal-preview" style="background:${ROUTE_META[e.route]?.color || '#888'}22;color:${ROUTE_META[e.route]?.color || '#888'}">★</div>
      <div class="gal-title">${routeName} – ${kindLabel}</div>
      <div class="gal-sub">${e.prose?.slice(0, 80) || ''}${e.prose?.length > 80 ? '…' : ''}</div>
    `;
    container.appendChild(card);
  }
}

function renderGalleryMemories(container) {
  const memSet = new Set();
  if (state?.relationships) {
    for (const rel of Object.values(state.relationships)) {
      if (rel.memories) rel.memories.forEach(m => memSet.add(m));
    }
  }
  const stored = JSON.parse(localStorage.getItem('bagger_memories') || '[]');
  stored.forEach(m => memSet.add(m));

  if (!memSet.size) {
    container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:40px">Noch keine Erinnerungen gesammelt.</p>';
    return;
  }
  for (const m of memSet) {
    const card = document.createElement('div');
    card.className = 'gal-card';
    card.innerHTML = `
      <div class="gal-preview" style="background:var(--gold)11;color:var(--gold)">📜</div>
      <div class="gal-title">Erinnerung</div>
      <div class="gal-sub">${m.slice(0, 100)}${m.length > 100 ? '…' : ''}</div>
    `;
    container.appendChild(card);
  }
}

function renderGalleryMusic(container) {
  container.innerHTML = `
    <div style="grid-column:1/-1;text-align:center;padding:40px;color:var(--muted)">
      <p style="font-size:2rem;margin-bottom:12px">🎵</p>
      <p>Musikzimmer</p>
      <p style="font-size:.85rem;margin-top:8px">Die Klänge der Bauhofnächte …<br>Atmosphäre-Texte und Stimmungsbilder.</p>
      <div style="display:grid;gap:8px;margin-top:20px;max-width:400px;margin-left:auto;margin-right:auto">
        <div class="gal-card" style="border:1px solid var(--line)">
          <div class="gal-title">Leise Hydraulik</div>
          <div class="gal-sub">Ein gleichmässiges Zischen, das an warme Umarmungen erinnert.</div>
        </div>
        <div class="gal-card" style="border:1px solid var(--line)">
          <div class="gal-title">Regen auf dem Schrottplatz</div>
          <div class="gal-sub">Tropfen, die auf altem Metall tanzen.</div>
        </div>
        <div class="gal-card" style="border:1px solid var(--line)">
          <div class="gal-title">Sternenlicht-Melodie</div>
          <div class="gal-sub">Was die Stille erzählt, wenn niemand spricht.</div>
        </div>
      </div>
    </div>
  `;
}

document.addEventListener('click', e => {
  const tab = e.target.closest('.gtab');
  if (!tab) return;
  document.querySelectorAll('.gtab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  galleryTab = tab.dataset.tab;
  renderGallery();
});

/* ═══════════════════════════════════════
   ENDING SCREEN
   ═══════════════════════════════════════ */
function showEndingScreen(ending, prose, finalState) {
  showScreen('ending');
  D.nvlLines().innerHTML = '';
  const route = ending.route || finalState?.currentRoute || 'aurora';
  const meta = ROUTE_META[route];
  const routeName = meta?.name || route;
  const kindLabel = ENDING_KIND_LABELS[ending.kind] || ending.kind;

  $('#ending-route-name').textContent = `${routeName} · ${gameData?.baggers?.[route]?.routeWord || ''}`;
  $('#ending-title').textContent = kindLabel;

  const proseEl = $('#ending-prose');
  proseEl.innerHTML = '';
  const finalText = ending.prose || prose || '';
  const lines = finalText.split('\n').filter(l => l.trim());
  for (const line of lines) {
    const p = document.createElement('p');
    p.className = 'ep-line';
    p.textContent = line;
    proseEl.appendChild(p);
  }

  if (finalState) {
    const statsEl = $('#ending-stats');
    statsEl.classList.remove('hidden');
    statsEl.innerHTML = `
      <span><strong>${finalState.day || '?'}</strong> Tage</span>
      <span><strong>${ending.kind === 'bad' ? '-' : finalState.relationships?.[route]?.bond || '?'}%</strong> Bindung</span>
      <span><strong>${finalState.relationships?.[route]?.dates || 0}</strong> Dates</span>
      <span><strong>${finalState.relationships?.[route]?.memories?.length || 0}</strong> Erinnerungen</span>
    `;

    storeEnding(ending, finalState);

    $('#ending-unlock').classList.remove('hidden');
    let unlockText = ending.kind === 'secret' ? '✦ Geheimes Ende freigeschaltet!' 
      : ending.kind === 'true' ? '★ Wahres Ende freigeschaltet!'
      : ending.kind === 'bad' ? 'Bad End erhalten.'
      : `✓ "${kindLabel}" freigeschaltet.`;
    $('#ending-unlock').textContent = unlockText;
  }

  const endingBg = $('#ending-bg');
  endingBg.style.background = `radial-gradient(ellipse at center, ${meta?.color || '#ffbf46'}22, transparent 60%)`;
}

$('#ending-to-menu')?.addEventListener('click', () => {
  showScreen('main-menu');
});

$('#ending-to-gallery')?.addEventListener('click', () => {
  showScreen('main-menu');
  setTimeout(() => { galleryTab = 'endings'; openGallery(); }, 100);
});

function storeEnding(ending, finalState) {
  try {
    const endings = JSON.parse(localStorage.getItem('bagger_endings') || '[]');
    const exists = endings.some(e => e.route === ending.route && e.kind === ending.kind);
    if (!exists) {
      endings.push({
        route: ending.route,
        kind: ending.kind,
        label: ENDING_KIND_LABELS[ending.kind] || ending.kind,
        prose: ending.prose || '',
        day: finalState.day,
        timestamp: Date.now(),
      });
      localStorage.setItem('bagger_endings', JSON.stringify(endings));
    }
    const memories = JSON.parse(localStorage.getItem('bagger_memories') || '[]');
    const rel = finalState.relationships?.[ending.route];
    if (rel?.memories) {
      for (const m of rel.memories) {
        if (!memories.includes(m)) memories.push(m);
      }
      localStorage.setItem('bagger_memories', JSON.stringify(memories));
    }
  } catch {}
}

/* ═══════════════════════════════════════
   BACKLOG
   ═══════════════════════════════════════ */
function addToBacklog(speaker, text, route, chapter) {
  backlog.push({ speaker, text, route, chapter, day: state?.day, period: PERIODS[state?.periodIndex] });
  if (backlog.length > 300) backlog.shift();
}

function openBacklog() {
  const dialog = document.getElementById('backlog-dialog');
  if (!dialog) return;

  const filter = dialog.querySelector('#backlog-filter');
  const routeEls = new Set(backlog.map(b => b.route).filter(Boolean));
  filter.innerHTML = '<option value="all">Alle</option>';
  for (const r of routeEls) {
    const opt = document.createElement('option');
    opt.value = r; opt.textContent = ROUTE_META[r]?.name || r;
    filter.appendChild(opt);
  }
  renderBacklog(filter.value);
  dialog.showModal();

  filter.onchange = () => renderBacklog(filter.value);
}

function renderBacklog(routeFilter) {
  const list = document.getElementById('backlog-list');
  list.innerHTML = '';
  const items = routeFilter === 'all' ? backlog : backlog.filter(b => b.route === routeFilter);
  if (!items.length) {
    list.innerHTML = '<p style="color:var(--muted)">Keine Einträge.</p>';
    return;
  }
  for (const b of items.slice(-100)) {
    const el = document.createElement('div');
    el.className = 'bl-entry';
    const name = b.speaker === '_narrator_' ? 'Erzähler' : b.speaker || '???';
    el.innerHTML = `
      <div class="bl-meta">${b.chapter ? b.chapter + ' · ' : ''}Tag ${b.day || '?'} ${b.period || ''} — ${name}</div>
      <div class="bl-text">${b.text}</div>
    `;
    list.appendChild(el);
  }
  list.scrollTop = list.scrollHeight;
}

/* ═══════════════════════════════════════
   THREE.JS — CHARACTER MODEL
   ═══════════════════════════════════════ */
let modelInitialized = false;
let currentModelRoute = null;

async function initModelStage() {
  if (modelInitialized) return;
  const stage = D.modelStage();
  if (!stage) return;

  const rect = stage.getBoundingClientRect();
  const w = rect.width || 300;
  const h = rect.height || 400;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(35, w / h, 0.1, 50);
  camera.position.set(0, 1, 6);
  camera.lookAt(0, 0.5, 0);

  const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
  renderer.setSize(w, h);
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  stage.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0x404060, 0.4);
  scene.add(ambient);

  const key = new THREE.DirectionalLight(0xffeedd, 1.2);
  key.position.set(3, 4, 4);
  scene.add(key);

  const fill = new THREE.DirectionalLight(0x8888ff, 0.3);
  fill.position.set(-3, 2, 3);
  scene.add(fill);

  const rim = new THREE.DirectionalLight(0xffbf46, 0.6);
  rim.position.set(-2, 1, -4);
  scene.add(rim);

  const hemi = new THREE.HemisphereLight(0x4466ff, 0x222244, 0.6);
  scene.add(hemi);

  modelScene = scene;
  modelRenderer = renderer;

  const resizeObserver = new ResizeObserver(() => {
    const r = stage.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      renderer.setSize(r.width, r.height);
      camera.aspect = r.width / r.height;
      camera.updateProjectionMatrix();
    }
  });
  resizeObserver.observe(stage);

  modelInitialized = true;

  function animate() {
    modelAnimId = requestAnimationFrame(animate);
    if (modelMesh) {
      modelMesh.rotation.y += 0.005;
      modelMesh.position.y = 0.5 + Math.sin(Date.now() * 0.001) * 0.03;
    }
    renderer.render(scene, camera);
  }
  animate();
}

async function loadCharacterModel(route) {
  if (!modelInitialized || !modelScene || route === currentModelRoute) return;
  currentModelRoute = route;

  if (modelMesh) {
    modelScene.remove(modelMesh);
    modelMesh.geometry?.dispose();
    modelMesh.material?.dispose();
    modelMesh = null;
  }

  const meta = ROUTE_META[route || 'aurora'];
  const color = meta?.colorHex || 0xffbf46;

  const geo = new THREE.Group();

  const bodyGeo = new THREE.CylinderGeometry(0.8, 1.0, 1.8, 12);
  const bodyMat = new THREE.MeshStandardMaterial({
    color, metalness: 0.7, roughness: 0.3,
    emissive: color, emissiveIntensity: 0.08,
  });
  const body = new THREE.Mesh(bodyGeo, bodyMat);
  body.position.y = 0.9;
  body.castShadow = true;
  geo.add(body);

  const cabGeo = new THREE.SphereGeometry(0.55, 10, 10);
  const cabMat = new THREE.MeshStandardMaterial({
    color: 0x222233, metalness: 0.9, roughness: 0.1,
    emissive: 0x4466aa, emissiveIntensity: 0.15,
  });
  const cab = new THREE.Mesh(cabGeo, cabMat);
  cab.position.y = 2.0;
  cab.scale.set(1, 0.9, 0.8);
  cab.castShadow = true;
  geo.add(cab);

  const visorGeo = new THREE.CylinderGeometry(0.3, 0.35, 0.15, 8);
  const visorMat = new THREE.MeshStandardMaterial({
    color: 0x88ccff, metalness: 0.1, roughness: 0.2,
    emissive: 0x88ccff, emissiveIntensity: 0.2,
  });
  const visor = new THREE.Mesh(visorGeo, visorMat);
  visor.position.set(0, 2.15, -0.45);
  visor.rotation.x = 0.3;
  geo.add(visor);

  const wheelGeo = new THREE.CylinderGeometry(0.25, 0.3, 0.15, 8);
  const wheelMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
  for (let x of [-0.5, 0.5]) {
    for (let z of [-0.5, 0.5]) {
      const w = new THREE.Mesh(wheelGeo, wheelMat);
      w.position.set(x, 0.1, z);
      w.rotation.x = Math.PI / 2;
      geo.add(w);
    }
  }

  const rim2Geo = new THREE.TorusGeometry(0.35, 0.03, 6, 12);
  const rim2Mat = new THREE.MeshStandardMaterial({
    color: 0xffbf46, emissive: 0xffbf46, emissiveIntensity: 0.1, transparent: true, opacity: 0.4,
  });
  const rim2 = new THREE.Mesh(rim2Geo, rim2Mat);
  rim2.position.y = 1.6;
  rim2.rotation.x = Math.PI / 2;
  geo.add(rim2);

  const glowGeo = new THREE.SphereGeometry(0.05, 6, 6);
  const glowMat = new THREE.MeshBasicMaterial({ color: 0xffffff });
  const glow = new THREE.Mesh(glowGeo, glowMat);
  glow.position.set(0, 2.0, 0.42);
  geo.add(glow);

  modelScene.add(geo);
  modelMesh = geo;
}

function setCharacterVisual(visual) {
  if (!modelMesh) return;
  const intensityMap = {
    listening: 0.2, shy: 0.1, proud: 0.3, guarded: 0.05,
    digging: 0.25, crisis: 0.4, confession: 0.35,
  };
  const intensity = intensityMap[visual] || 0.15;
  modelMesh.children.forEach(child => {
    if (child.material && child.material.emissiveIntensity !== undefined) {
      child.material.emissiveIntensity = intensity;
    }
  });
}

/* ═══════════════════════════════════════
   MAIN MENU BUTTONS
   ═══════════════════════════════════════ */
$('#menu-new-game')?.addEventListener('click', async () => {
  showScreen('setup');
  await populateSetup();
});
$('#menu-load')?.addEventListener('click', openSaveLoad);
$('#menu-gallery')?.addEventListener('click', () => { galleryTab = 'endings'; openGallery(); });
$('#menu-settings')?.addEventListener('click', openSettings);

/* ═══════════════════════════════════════
   KEYBOARD SHORTCUTS
   ═══════════════════════════════════════ */
document.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA' || e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;

  if (e.key === 'a' || e.key === 'A') { if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); toggleAuto(); } }
  if (e.key === 's' || e.key === 'S') { if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); toggleSkip(); } }
  if (e.key === 'n' || e.key === 'N') { e.preventDefault(); toggleNvlMode(); }
  if (e.key === 'h' || e.key === 'H') { e.preventDefault(); toggleHide(); }
  if (e.key === 'l' || e.key === 'L') { if (!e.ctrlKey && !e.metaKey) { e.preventDefault(); openBacklog(); } }
  if (e.key === 'Escape') {
    const dialog = document.getElementById('backlog-dialog');
    if (dialog?.open) { dialog.close(); return; }
    const openOverlay = document.querySelector('.overlay-screen:not(.hidden)');
    if (openOverlay) { openOverlay.classList.add('hidden'); return; }
  }
});

/* ═══════════════════════════════════════
   INIT
   ═══════════════════════════════════════ */
async function init() {
  loadSettingsFromStorage();
  try { gameData = await apiGet('/game-data'); } catch (err) { console.error('game-data:', err); }
  applySettings();
  showScreen('main-menu');
  initModelStage();
  setupAdvancer();
}

init();

export default {
  state, gameData, settings, advance, openSchedule, openDate, openStatus,
  openSaveLoad, openGallery, openBacklog, openSettings,
};
