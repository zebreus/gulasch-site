const pokemon = [
  { id: 25, name: "Pikachu" },
  { id: 1, name: "Bulbasaur" },
  { id: 4, name: "Charmander" },
  { id: 7, name: "Squirtle" },
  { id: 10, name: "Caterpie" },
  { id: 16, name: "Pidgey" },
  { id: 19, name: "Rattata" },
  { id: 37, name: "Vulpix" },
  { id: 39, name: "Jigglypuff" },
  { id: 43, name: "Oddish" },
  { id: 50, name: "Diglett" },
  { id: 52, name: "Meowth" },
  { id: 54, name: "Psyduck" },
  { id: 58, name: "Growlithe" },
  { id: 63, name: "Abra" },
  { id: 66, name: "Machop" },
  { id: 74, name: "Geodude" },
  { id: 79, name: "Slowpoke" },
  { id: 81, name: "Magnemite" },
  { id: 84, name: "Doduo" },
  { id: 86, name: "Seel" },
  { id: 88, name: "Grimer" },
  { id: 94, name: "Gengar" },
  { id: 95, name: "Onix" },
  { id: 96, name: "Drowzee" },
  { id: 98, name: "Krabby" },
  { id: 100, name: "Voltorb" },
  { id: 104, name: "Cubone" },
  { id: 109, name: "Koffing" },
  { id: 111, name: "Rhyhorn" },
  { id: 113, name: "Chansey" },
  { id: 118, name: "Goldeen" },
  { id: 120, name: "Staryu" },
  { id: 122, name: "Mr. Mime" },
  { id: 123, name: "Scyther" },
  { id: 124, name: "Jynx" },
  { id: 125, name: "Electabuzz" },
  { id: 126, name: "Magmar" },
  { id: 129, name: "Magikarp" },
  { id: 131, name: "Lapras" },
  { id: 132, name: "Ditto" },
  { id: 133, name: "Eevee" },
  { id: 143, name: "Snorlax" },
  { id: 147, name: "Dratini" },
  { id: 149, name: "Dragonite" },
  { id: 150, name: "Mewtwo" },
  { id: 151, name: "Mew" }
];

const bosses = [
  { id: 94, name: "Gengar Raid", hp: 62, reward: 24 },
  { id: 130, name: "Gyarados Raid", hp: 74, reward: 30 },
  { id: 143, name: "Snorlax Raid", hp: 86, reward: 34 },
  { id: 149, name: "Dragonite Raid", hp: 94, reward: 42 },
  { id: 150, name: "Mewtwo Raid", hp: 120, reward: 60 }
];

const bet = 3;
const refillCredits = 30;
const dailyGoal = 10;
const overdriveMax = 100;
const overdriveLength = 12;
const missionSlots = 3;
const speedModes = [
  { label: "x1", interval: 90, base: 850, stagger: 360, autoDelay: 500, pops: 1 },
  { label: "x2", interval: 58, base: 560, stagger: 230, autoDelay: 260, pops: 2 },
  { label: "x4", interval: 38, base: 340, stagger: 140, autoDelay: 120, pops: 3 },
  { label: "MAX", interval: 24, base: 210, stagger: 76, autoDelay: 60, pops: 5 }
];
const brainrotLines = [
  "pikachu economy is in shambles",
  "one more spin fixes everything",
  "critical goblin mode detected",
  "meowth saw the spreadsheet and left",
  "dopamine used thunderbolt",
  "rare candy pipeline online",
  "snorlax says lock in",
  "squirtle squad fiscal quarter",
  "jigglypuff sleep debt maxed",
  "gengar is shorting your credits",
  "raid boss failed the vibe check",
  "overdrive goblin has entered chat",
  "mewtwo watching the metrics",
  "magikarp pivoted to fintech",
  "collection brain activated"
];
const stateKey = "pokemon-slot-state";
const today = new Date().toISOString().slice(0, 10);
const legacyCredits = Number.parseInt(window.localStorage.getItem("pokemon-slot-credits"), 10);
let saved = {};

try {
  saved = JSON.parse(window.localStorage.getItem(stateKey) || "{}");
} catch {
  saved = {};
}

const state = {
  credits: Number.isFinite(saved.credits) ? saved.credits : Number.isNaN(legacyCredits) ? 30 : legacyCredits,
  bestCredits: Number.isFinite(saved.bestCredits) ? saved.bestCredits : 30,
  lastWin: 0,
  doubleBank: 0,
  speed: Number.isInteger(saved.speed) && saved.speed >= 0 && saved.speed < speedModes.length ? saved.speed : 0,
  brainrot: Boolean(saved.brainrot),
  overdriveCharge: Number.isFinite(saved.overdriveCharge) ? Math.min(overdriveMax, saved.overdriveCharge) : 0,
  overdriveSpins: Number.isFinite(saved.overdriveSpins) ? Math.max(0, saved.overdriveSpins) : 0,
  overdrives: Number.isFinite(saved.overdrives) ? saved.overdrives : 0,
  raid: normalizeRaid(saved.raid, saved.raidDefeats),
  raidDefeats: Number.isFinite(saved.raidDefeats) ? saved.raidDefeats : 0,
  streak: Number.isFinite(saved.streak) ? saved.streak : 0,
  spins: Number.isFinite(saved.spins) ? saved.spins : 0,
  sessionSpins: 0,
  shiny: Number.isFinite(saved.shiny) ? saved.shiny : 0,
  caught: Array.isArray(saved.caught) ? saved.caught.filter((id) => pokemon.some((pick) => pick.id === id)) : [],
  achievements: Array.isArray(saved.achievements) ? saved.achievements : [],
  missions: normalizeMissions(saved.missions, saved.mission),
  dailyDate: saved.dailyDate === today ? saved.dailyDate : today,
  dailySpins: saved.dailyDate === today && Number.isFinite(saved.dailySpins) ? saved.dailySpins : 0,
  dailyClaimed: saved.dailyDate === today ? Boolean(saved.dailyClaimed) : false
};

let spinning = false;
let autoRemaining = 0;
let toastTimer;

const reels = [...document.querySelectorAll(".reel")];
const message = document.querySelector("#message");
const creditsEl = document.querySelector("#credits");
const lastWinEl = document.querySelector("#last-win");
const streakEl = document.querySelector("#streak");
const levelEl = document.querySelector("#level");
const caughtEl = document.querySelector("#caught");
const bestEl = document.querySelector("#best");
const shinyEl = document.querySelector("#shiny");
const overdriveStatEl = document.querySelector("#overdrive-stat");
const raidsEl = document.querySelector("#raids");
const dailyEl = document.querySelector("#daily");
const dailyMeter = document.querySelector("#daily-meter");
const collectionEl = document.querySelector("#collection");
const milestonesEl = document.querySelector("#milestones");
const heatEl = document.querySelector("#heat");
const heatMeter = document.querySelector("#heat-meter");
const missionsEl = document.querySelector("#missions");
const overdriveStatus = document.querySelector("#overdrive-status");
const overdriveMeter = document.querySelector("#overdrive-meter");
const raidEl = document.querySelector("#raid");
const raidMeter = document.querySelector("#raid-meter");
const ticker = document.querySelector("#ticker");
const spinButton = document.querySelector("#spin");
const autoButton = document.querySelector("#auto");
const speedButton = document.querySelector("#speed");
const overdriveButton = document.querySelector("#overdrive");
const chaosButton = document.querySelector("#chaos");
const doubleButton = document.querySelector("#double");
const refillButton = document.querySelector("#refill");
const payment = document.querySelector("#payment");
const refillForm = document.querySelector("#refill-form");
const refillAmount = document.querySelector("#refill-amount");
const refillNotes = document.querySelector("#refill-notes");
const closePayment = document.querySelector("#close-payment");
const toast = document.querySelector("#toast");
const popLayer = document.querySelector("#pop-layer");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function spriteUrl(id) {
  return `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/${id}.png`;
}

function speedMode() {
  return speedModes[state.speed] || speedModes[0];
}

function effectiveSpeedMode() {
  return state.overdriveSpins > 0 ? speedModes[speedModes.length - 1] : speedMode();
}

function randomPokemon() {
  return pokemon[Math.floor(Math.random() * pokemon.length)];
}

function createMission() {
  const pick = randomPokemon();
  const templates = [
    { type: "spins", label: "Spin 5 times", target: 5, progress: 0, reward: 6 },
    { type: "speedSpin", label: "Fast-spin 8 times", target: 8, progress: 0, reward: 9 },
    { type: "brainrot", label: "Brainrot 8 spins", target: 8, progress: 0, reward: 9 },
    { type: "win", label: "Hit 2 wins", target: 2, progress: 0, reward: 12 },
    { type: "pair", label: "Land 2 pairs", target: 2, progress: 0, reward: 14 },
    { type: "triple", label: "Land a triple", target: 1, progress: 0, reward: 26 },
    { type: "catchAny", label: "Land 4 Pokemon", target: 4, progress: 0, reward: 10 },
    { type: "catch", label: `Land ${pick.name}`, target: 1, progress: 0, reward: 16, pokemon: pick.id },
    { type: "shiny", label: "Find a shiny", target: 1, progress: 0, reward: 24 },
    { type: "streak", label: "Build 3 streak", target: 3, progress: 0, reward: 18 },
    { type: "raid", label: "Deal 24 raid damage", target: 24, progress: 0, reward: 14 },
    { type: "boss", label: "Defeat a raid boss", target: 1, progress: 0, reward: 28 },
    { type: "overdrive", label: "Spend 3 Overdrive spins", target: 3, progress: 0, reward: 16 },
    { type: "overdriveStart", label: "Activate Overdrive", target: 1, progress: 0, reward: 20 }
  ];
  const mission = { ...templates[Math.floor(Math.random() * templates.length)] };
  mission.key = `${mission.type}-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
  return mission;
}

function validMission(mission) {
  return mission && mission.type && Number.isFinite(mission.target) && Number.isFinite(mission.progress) && Number.isFinite(mission.reward);
}

function normalizeMissions(savedMissions, legacyMission) {
  const missions = [];
  const source = Array.isArray(savedMissions) ? savedMissions : legacyMission ? [legacyMission] : [];

  source.forEach((mission) => {
    if (validMission(mission) && missions.length < missionSlots) {
      missions.push({ ...mission, progress: Math.min(mission.progress, mission.target) });
    }
  });

  while (missions.length < missionSlots) {
    missions.push(createMission());
  }

  return missions;
}

function createRaid(defeats = 0) {
  const boss = bosses[Math.floor(Math.random() * bosses.length)];
  const scale = Math.min(60, Math.floor(defeats * 5));
  const maxHp = boss.hp + scale;
  return {
    id: boss.id,
    name: boss.name,
    hp: maxHp,
    maxHp,
    reward: boss.reward + Math.floor(scale / 3)
  };
}

function normalizeRaid(raid, defeats = 0) {
  if (raid && Number.isFinite(raid.hp) && Number.isFinite(raid.maxHp) && Number.isFinite(raid.reward) && raid.name) {
    return { ...raid, hp: Math.max(1, Math.min(raid.hp, raid.maxHp)) };
  }

  return createRaid(Number.isFinite(defeats) ? defeats : 0);
}

function ensureMissions() {
  state.missions = normalizeMissions(state.missions, null);
}

function randomBrainrotLine() {
  return brainrotLines[Math.floor(Math.random() * brainrotLines.length)];
}

function setVisualModes() {
  document.body.classList.toggle("brainrot", state.brainrot && !reducedMotion);
  document.body.classList.toggle("overdrive", state.overdriveSpins > 0 && !reducedMotion);
  chaosButton.setAttribute("aria-pressed", String(state.brainrot));
  chaosButton.textContent = state.brainrot ? "Brainrot On" : "Brainrot Off";
}

function hype(text) {
  ticker.textContent = text;
  if (state.brainrot || state.overdriveSpins > 0) spawnPops(text, effectiveSpeedMode().pops + (state.overdriveSpins > 0 ? 2 : 0));
}

function spawnPops(text, count = 1) {
  if (reducedMotion) return;

  for (let index = 0; index < count; index += 1) {
    const pop = document.createElement("div");
    pop.className = "pop";
    pop.textContent = text.length > 24 ? text.slice(0, 24) : text;
    pop.style.setProperty("--x", `${12 + Math.random() * 76}%`);
    pop.style.setProperty("--y", `${16 + Math.random() * 62}%`);
    popLayer.append(pop);
    window.setTimeout(() => pop.remove(), 1100);
  }

  while (popLayer.children.length > 24) {
    popLayer.firstElementChild.remove();
  }
}

function saveState() {
  window.localStorage.setItem(stateKey, JSON.stringify(state));
}

function pickPokemon() {
  const shinyChance = state.overdriveSpins > 0 ? 0.085 : state.brainrot ? 0.035 : 0.025;
  return { ...randomPokemon(), shiny: Math.random() < shinyChance };
}

function setReel(reel, pick) {
  const image = reel.querySelector("img");
  const title = reel.querySelector("h2");
  image.src = spriteUrl(pick.id);
  image.alt = pick.name;
  title.textContent = pick.shiny ? `Shiny ${pick.name}` : pick.name;
  reel.classList.toggle("shiny", Boolean(pick.shiny));
}

function trainerLevel() {
  return Math.max(1, Math.floor(state.spins / 10) + Math.floor(state.caught.length / 4) + state.raidDefeats + state.overdrives + 1);
}

function showToast(text) {
  window.clearTimeout(toastTimer);
  toast.textContent = text;
  toast.hidden = false;
  if (state.brainrot || state.overdriveSpins > 0) spawnPops(text, Math.max(1, effectiveSpeedMode().pops));
  toastTimer = window.setTimeout(() => {
    toast.hidden = true;
  }, 2600);
}

function unlock(id, text, reward = 0) {
  if (state.achievements.includes(id)) return;
  state.achievements.push(id);
  state.credits += reward;
  chargeOverdrive(8);
  showToast(reward > 0 ? `${text} +${reward} credits` : text);
}

function score(results) {
  const [first, second, third] = results;

  if (first.id === 25 && second.id === 25 && third.id === 25) {
    return { win: 60, text: "Pikachu jackpot!", kind: "jackpot" };
  }

  if (first.id === second.id && second.id === third.id) {
    return { win: 30, text: `Triple ${first.name}!`, kind: "triple" };
  }

  if (first.id === second.id || first.id === third.id || second.id === third.id) {
    return { win: 7, text: "Pair caught!", kind: "pair" };
  }

  return { win: 0, text: "No match. Raid chip damage applied.", kind: "miss" };
}

function renderCollection() {
  collectionEl.innerHTML = "";

  pokemon.forEach((pick) => {
    const image = document.createElement("img");
    image.src = spriteUrl(pick.id);
    image.alt = state.caught.includes(pick.id) ? pick.name : "Unknown Pokemon";
    image.title = state.caught.includes(pick.id) ? pick.name : "Not caught yet";
    image.className = state.caught.includes(pick.id) ? "caught" : "";
    collectionEl.append(image);
  });
}

function renderMilestones() {
  const milestones = [
    { label: "20 spins", done: state.spins >= 20 },
    { label: "100 spins", done: state.spins >= 100 },
    { label: "5 streak", done: state.streak >= 5 },
    { label: "100 credits", done: state.bestCredits >= 100 },
    { label: "20 caught", done: state.caught.length >= 20 },
    { label: "all caught", done: state.caught.length === pokemon.length },
    { label: "3 shinies", done: state.shiny >= 3 },
    { label: "3 raids", done: state.raidDefeats >= 3 },
    { label: "5 overdrives", done: state.overdrives >= 5 }
  ];

  milestonesEl.innerHTML = "";
  milestones.forEach((milestone) => {
    const item = document.createElement("li");
    item.className = milestone.done ? "done" : "";
    item.innerHTML = `<span>${milestone.label}</span><strong>${milestone.done ? "done" : "open"}</strong>`;
    milestonesEl.append(item);
  });
}

function renderMissions() {
  ensureMissions();
  missionsEl.innerHTML = "";

  state.missions.forEach((mission) => {
    const progress = Math.min(mission.progress, mission.target);
    const card = document.createElement("article");
    card.className = "mission-card";
    card.innerHTML = `<strong>${mission.label}</strong><small>${progress}/${mission.target} for +${mission.reward} credits</small><div class="meter mission"><span style="width:${(progress / mission.target) * 100}%"></span></div>`;
    missionsEl.append(card);
  });
}

function updateStats() {
  ensureMissions();
  const dailyProgress = Math.min(state.dailySpins, dailyGoal);
  const heat = Math.min(state.sessionSpins, 25);
  const overdriveProgress = state.overdriveSpins > 0 ? (state.overdriveSpins / overdriveLength) * 100 : state.overdriveCharge;
  const raidProgress = Math.max(0, (state.raid.hp / state.raid.maxHp) * 100);

  state.bestCredits = Math.max(state.bestCredits, state.credits);
  state.overdriveCharge = Math.min(overdriveMax, Math.max(0, state.overdriveCharge));

  creditsEl.textContent = state.credits;
  lastWinEl.textContent = state.lastWin;
  streakEl.textContent = state.streak;
  levelEl.textContent = trainerLevel();
  caughtEl.textContent = `${state.caught.length}/${pokemon.length}`;
  bestEl.textContent = state.bestCredits;
  shinyEl.textContent = state.shiny;
  overdriveStatEl.textContent = state.overdriveSpins > 0 ? `${state.overdriveSpins}x` : `${state.overdriveCharge}%`;
  raidsEl.textContent = state.raidDefeats;
  dailyMeter.style.width = `${(dailyProgress / dailyGoal) * 100}%`;
  heatMeter.style.width = `${(heat / 25) * 100}%`;
  overdriveMeter.style.width = `${overdriveProgress}%`;
  raidMeter.style.width = `${raidProgress}%`;
  heatEl.textContent = heat >= 25 ? "Max heat. Wins pay +3 bonus credits." : `${25 - heat} spins until max heat bonus.`;
  overdriveStatus.textContent = state.overdriveSpins > 0
    ? `OVERDRIVE ACTIVE: ${state.overdriveSpins} boosted spins left.`
    : state.overdriveCharge >= overdriveMax
      ? "Overdrive ready. Hit the button and melt the machine."
      : `${overdriveMax - state.overdriveCharge}% charge until Overdrive.`;
  raidEl.textContent = `${state.raid.name}: ${Math.max(0, state.raid.hp)}/${state.raid.maxHp} HP, defeat for +${state.raid.reward} credits.`;
  dailyEl.textContent = state.dailyClaimed
    ? "Daily bonus claimed. Come back tomorrow."
    : `Spin ${dailyGoal - dailyProgress} more time${dailyGoal - dailyProgress === 1 ? "" : "s"} today for +12 credits.`;
  spinButton.textContent = state.credits >= bet ? "Spin" : "Refill Credits";
  autoButton.textContent = autoRemaining > 0 ? `Auto ${autoRemaining}` : state.overdriveSpins > 0 ? "Auto x50" : state.brainrot ? "Auto x25" : "Auto x10";
  speedButton.textContent = `Speed ${speedMode().label}`;
  overdriveButton.disabled = spinning || state.overdriveSpins > 0 || state.overdriveCharge < overdriveMax;
  overdriveButton.textContent = state.overdriveSpins > 0 ? `OD ${state.overdriveSpins}` : state.overdriveCharge >= overdriveMax ? "Overdrive" : `OD ${state.overdriveCharge}%`;
  doubleButton.disabled = spinning || state.doubleBank <= 0;
  doubleButton.textContent = state.doubleBank > 0 ? `Double ${state.doubleBank}` : "Double";
  setVisualModes();
  renderCollection();
  renderMilestones();
  renderMissions();
  saveState();
}

function missionMatches(mission, type, meta) {
  if (mission.type !== type) return false;
  if (mission.type === "catch") return mission.pokemon === meta.id;
  return true;
}

function advanceMission(type, amount = 1, meta = {}) {
  ensureMissions();

  state.missions = state.missions.map((mission) => {
    if (!missionMatches(mission, type, meta)) return mission;

    const next = { ...mission, progress: Math.min(mission.target, mission.progress + amount) };
    if (next.progress < next.target) return next;

    state.credits += next.reward;
    chargeOverdrive(6);
    showToast(`Mission complete! +${next.reward} credits`);
    hype(`quest cleared +${next.reward}`);
    return createMission();
  });
}

function syncMission(type, value) {
  ensureMissions();

  state.missions = state.missions.map((mission) => {
    if (mission.type !== type) return mission;
    const next = { ...mission, progress: Math.min(mission.target, Math.max(mission.progress, value)) };
    if (next.progress < next.target) return next;

    state.credits += next.reward;
    chargeOverdrive(6);
    showToast(`Mission complete! +${next.reward} credits`);
    hype(`quest cleared +${next.reward}`);
    return createMission();
  });
}

function chargeOverdrive(amount) {
  if (state.overdriveSpins > 0) return;
  const before = state.overdriveCharge;
  state.overdriveCharge = Math.min(overdriveMax, state.overdriveCharge + amount);
  if (before < overdriveMax && state.overdriveCharge >= overdriveMax) {
    showToast("Overdrive ready");
    hype("overdrive ready");
  }
}

function activateOverdrive() {
  if (spinning || state.overdriveSpins > 0 || state.overdriveCharge < overdriveMax) return;

  state.overdriveCharge = 0;
  state.overdriveSpins = overdriveLength;
  state.overdrives += 1;
  advanceMission("overdriveStart");
  showToast("OVERDRIVE ACTIVATED");
  hype("overdrive activated");
  updateStats();
}

function damageRaid(amount) {
  const damage = Math.max(1, Math.floor(amount));
  state.raid.hp -= damage;
  advanceMission("raid", damage);
  hype(`${damage} raid damage`);

  if (state.raid.hp > 0) return;

  state.credits += state.raid.reward;
  state.raidDefeats += 1;
  chargeOverdrive(25);
  advanceMission("boss");
  showToast(`${state.raid.name} defeated! +${state.raid.reward}`);
  hype("raid boss deleted");
  state.raid = createRaid(state.raidDefeats);
}

function catchResults(results) {
  results.forEach((pick) => {
    if (pick.shiny) {
      state.shiny += 1;
      state.credits += state.overdriveSpins > 0 ? 8 : 5;
      chargeOverdrive(10);
      advanceMission("shiny");
      showToast(`Shiny ${pick.name}! Bonus credits`);
    }

    advanceMission("catchAny");
    advanceMission("catch", 1, { id: pick.id });

    if (!state.caught.includes(pick.id)) {
      state.caught.push(pick.id);
      state.credits += 2;
      chargeOverdrive(4);
      showToast(`New catch: ${pick.name}! +2`);
    }
  });
}

function checkRewards(round) {
  if (round.win > 0) {
    state.streak += 1;
  } else {
    state.streak = 0;
  }

  state.spins += 1;
  state.sessionSpins += 1;
  state.dailySpins += 1;
  state.bestCredits = Math.max(state.bestCredits, state.credits);
  chargeOverdrive(3 + (round.win > 0 ? 7 : 0) + (round.kind === "jackpot" ? 20 : 0));
  advanceMission("spins");
  if (state.speed >= 2 || state.overdriveSpins > 0) advanceMission("speedSpin");
  if (state.brainrot) advanceMission("brainrot");
  if (round.win > 0) advanceMission("win");
  if (["pair", "triple", "jackpot"].includes(round.kind)) advanceMission("pair");
  if (["triple", "jackpot"].includes(round.kind)) advanceMission("triple");
  syncMission("streak", state.streak);

  if (round.win > 0 && state.sessionSpins >= 25) {
    state.credits += 3;
    round.text = `${round.text} Heat bonus +3.`;
  }

  if (state.dailySpins >= dailyGoal && !state.dailyClaimed) {
    state.dailyClaimed = true;
    state.credits += 12;
    chargeOverdrive(12);
    showToast("Daily quest complete! +12 credits");
  }

  if (state.brainrot && round.win === 0 && state.sessionSpins % 6 === 0) {
    state.credits += 1;
    hype("doomscroll rebate +1");
  }

  if (state.overdriveSpins > 0) {
    advanceMission("overdrive");
    state.overdriveSpins -= 1;
    if (state.overdriveSpins === 0) showToast("Overdrive cooled down");
  }

  const raidDamage = 1
    + (round.win > 0 ? Math.ceil(round.win / 6) : 0)
    + (round.kind === "triple" ? 4 : 0)
    + (round.kind === "jackpot" ? 12 : 0)
    + (state.overdriveSpins > 0 ? 3 : 0);
  damageRaid(raidDamage);

  if (state.streak >= 3) unlock("streak-3", "Hot streak unlocked!", 9);
  if (state.streak >= 5) unlock("streak-5", "Five-win streak badge!", 18);
  if (state.caught.length >= 5) unlock("caught-5", "Starter collector bonus!", 12);
  if (state.caught.length >= 20) unlock("caught-20", "Big Pokedex bonus!", 32);
  if (state.caught.length === pokemon.length) unlock("caught-all", "Full Pokedex jackpot!", 90);
  if (round.kind === "jackpot") unlock("pikachu-jackpot", "Pikachu legend badge!", 25);
  if (state.spins >= 50) unlock("spin-50", "50 spin grinder badge!", 20);
  if (state.spins >= 150) unlock("spin-150", "150 spin trance badge!", 45);
  if (state.bestCredits >= 100) unlock("credits-100", "Triple digit bankroll!", 12);
  if (state.bestCredits >= 250) unlock("credits-250", "Quarter kilo bankroll!", 40);
  if (state.shiny >= 3) unlock("shiny-3", "Shiny hunter badge!", 30);
  if (state.raidDefeats >= 3) unlock("raids-3", "Raid bully badge!", 35);
  if (state.overdrives >= 5) unlock("overdrive-5", "Overdrive addict badge!", 38);
}

function showPayment() {
  autoRemaining = 0;
  updateStats();
  payment.hidden = false;
  refillAmount.focus();
}

function hidePayment() {
  payment.hidden = true;
}

function refillAfterPayment() {
  const amount = Number.parseFloat(refillAmount.value || "0").toFixed(2);
  refillNotes.value = `Pokemon slot machine credit refill (${amount} EUR pay-what-you-want)`;
  state.credits += refillCredits;
  state.lastWin = 0;
  chargeOverdrive(10);
  message.textContent = `Refilled ${refillCredits} credits. Checkout opened in a new tab.`;
  hidePayment();
  updateStats();
}

function finishSpin(results) {
  const overdriveWasActive = state.overdriveSpins > 0;
  const round = score(results);
  if (round.win > 0 && overdriveWasActive) {
    round.win = Math.ceil(round.win * 1.6);
    round.text = `OVERDRIVE ${round.text}`;
  }

  state.credits += round.win;
  state.lastWin = round.win;
  state.doubleBank = round.win;
  catchResults(results);
  checkRewards(round);
  message.textContent = round.win > 0 && state.streak > 1 ? `${round.text} ${state.streak} win streak.` : round.text;
  hype(round.win > 0 ? `${round.kind} +${round.win}` : randomBrainrotLine());
  spinning = false;
  spinButton.disabled = false;
  autoButton.disabled = false;
  updateStats();

  if (autoRemaining > 0) {
    autoRemaining -= 1;
    updateStats();
    if (state.credits >= bet) {
      window.setTimeout(spin, effectiveSpeedMode().autoDelay);
    } else {
      message.textContent = "Autoroll paused. Refill to continue.";
      showPayment();
    }
  }
}

function spin() {
  if (spinning) return;

  const mode = effectiveSpeedMode();

  if (state.credits < bet) {
    message.textContent = "Out of credits. Refill to keep spinning.";
    showPayment();
    return;
  }

  spinning = true;
  state.doubleBank = 0;
  state.credits -= bet;
  state.lastWin = 0;
  updateStats();
  message.textContent = state.overdriveSpins > 0 ? "OVERDRIVE ROLLING..." : autoRemaining > 0 ? "Autorolling..." : "Reels are spinning...";
  spinButton.disabled = true;
  autoButton.disabled = true;
  spinButton.textContent = "Spinning";

  const results = [];
  const timers = reels.map((reel) => {
    reel.classList.add("spinning");
    return window.setInterval(() => setReel(reel, pickPokemon()), mode.interval);
  });

  reels.forEach((reel, index) => {
    window.setTimeout(() => {
      window.clearInterval(timers[index]);
      const pick = pickPokemon();
      results[index] = pick;
      setReel(reel, pick);
      reel.classList.remove("spinning");

      if (results.filter(Boolean).length === reels.length) {
        finishSpin(results);
      }
    }, mode.base + index * mode.stagger);
  });
}

function doubleOrNothing() {
  if (spinning || state.doubleBank <= 0) return;

  const bank = state.doubleBank;
  state.doubleBank = 0;

  if (Math.random() < (state.overdriveSpins > 0 ? 0.56 : 0.48)) {
    state.credits += bank;
    state.lastWin = bank * 2;
    chargeOverdrive(7);
    message.textContent = `Double hit! Banked ${bank * 2} total.`;
    hype(`double hit +${bank}`);
    showToast("Double-or-nothing won!");
  } else {
    state.credits = Math.max(0, state.credits - bank);
    state.lastWin = 0;
    state.streak = 0;
    message.textContent = "Double missed. The house took that win back.";
    hype("double got rugged");
  }

  updateStats();
}

function autoSpin() {
  if (spinning) return;
  autoRemaining = autoRemaining > 0 ? 0 : state.overdriveSpins > 0 ? 49 : state.brainrot ? 24 : 9;
  updateStats();
  if (autoRemaining > 0) spin();
}

function cycleSpeed() {
  if (spinning) return;
  state.speed = (state.speed + 1) % speedModes.length;
  hype(`speed ${speedMode().label}`);
  showToast(`Speed ${speedMode().label}`);
  updateStats();
}

function toggleBrainrot() {
  state.brainrot = !state.brainrot;
  if (state.brainrot && state.speed < 2) state.speed = 2;
  hype(state.brainrot ? "brainrot mode engaged" : "brainrot mode cooled down");
  showToast(state.brainrot ? "Brainrot mode on" : "Brainrot mode off");
  updateStats();
}

spinButton.addEventListener("click", spin);
autoButton.addEventListener("click", autoSpin);
speedButton.addEventListener("click", cycleSpeed);
overdriveButton.addEventListener("click", activateOverdrive);
chaosButton.addEventListener("click", toggleBrainrot);
doubleButton.addEventListener("click", doubleOrNothing);
refillButton.addEventListener("click", showPayment);
closePayment.addEventListener("click", hidePayment);
payment.addEventListener("click", (event) => {
  if (event.target === payment) hidePayment();
});
refillForm.addEventListener("submit", refillAfterPayment);
window.addEventListener("keydown", (event) => {
  if (["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) return;
  if (event.code === "Space") {
    event.preventDefault();
    spin();
  }
  if (event.key.toLowerCase() === "f") cycleSpeed();
  if (event.key.toLowerCase() === "b") toggleBrainrot();
  if (event.key.toLowerCase() === "o") activateOverdrive();
});
updateStats();
