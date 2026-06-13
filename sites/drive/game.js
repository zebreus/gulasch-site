const canvas = document.querySelector("#game");
const ctx = canvas.getContext("2d");
const lapTimeEl = document.querySelector("#lapTime");
const bestTimeEl = document.querySelector("#bestTime");
const checkpointEl = document.querySelector("#checkpoint");
const messageEl = document.querySelector("#message");
const driverForm = document.querySelector("#driverForm");
const driverNameEl = document.querySelector("#driverName");
const leaderboardListEl = document.querySelector("#leaderboardList");
const trackSelectEl = document.querySelector("#trackSelect");

const keys = new Set();
const bestKey = "gulasch-drive-3d-v9-best";
const driverKey = "gulasch-drive-driver";
const trackKey = "gulasch-drive-track";
const roadWidth = 130;
const cameraHeight = 92;
const focalLength = 740;
const horizon = 250;
let best = Number(localStorage.getItem(bestKey)) || 0;

const trackConfigs = {
  starter: {
    name: "Starter Sprint",
    points: [[0, 0], [420, 40], [760, 230], [690, 620], [260, 780], [-190, 610], [-380, 220], [-190, -90]],
    loopRange: [0.54, 0.62],
  },
  airfield: {
    name: "Airfield Sprint",
    points: [[0, 0], [500, 0], [1050, 0], [2200, 0], [2660, 360], [2500, 850], [1840, 1080], [1080, 880], [560, 1040], [-120, 790], [-470, 280], [-260, -140]],
  },
  alpine: {
    name: "Alpine Loop",
    points: [[0, 0], [420, 120], [840, -40], [1250, 260], [1180, 780], [730, 1050], [230, 880], [-220, 1040], [-620, 720], [-720, 250], [-390, -130]],
    loopRange: [0.42, 0.52],
  },
  dockside: {
    name: "Dockside Sprint",
    points: [[0, 0], [430, 0], [860, 250], [890, 760], [520, 1080], [-20, 1060], [-440, 750], [-560, 290], [-240, -80]],
  },
  nurburgring: {
    name: "Green Hell Inspired",
    points: [[0, 0], [320, -80], [760, 20], [1010, 260], [930, 560], [1190, 790], [990, 1080], [620, 1120], [390, 910], [110, 1040], [-240, 880], [-370, 550], [-650, 420], [-560, 100], [-760, -170], [-470, -390], [-70, -270]],
    loopRange: [0.7, 0.77],
  },
};

let activeTrackId = localStorage.getItem(trackKey) || "starter";
let activeTrack = trackConfigs[activeTrackId] || trackConfigs.starter;
let points = [];
let segments = [];
let trackLength = 0;
let checkpoints = [];
let loop = null;

function buildTrack(trackId) {
  activeTrackId = trackConfigs[trackId] ? trackId : "starter";
  activeTrack = trackConfigs[activeTrackId];
  localStorage.setItem(trackKey, activeTrackId);
  points = activeTrack.points.map(([x, z]) => ({ x, z }));
  segments = [];
  trackLength = 0;

  for (let i = 0; i < points.length; i += 1) {
    const a = points[i];
    const b = points[(i + 1) % points.length];
    const length = Math.hypot(b.x - a.x, b.z - a.z);
    segments.push({ a, b, start: trackLength, length });
    trackLength += length;
  }

  checkpoints = [0, 0.17, 0.34, 0.51, 0.68, 0.85].map((ratio, index) => ({
    s: ratio * trackLength,
    label: index === 0 ? "start" : `checkpoint ${index}`,
  }));

  const loopRange = activeTrack.loopRange || [0.58, 0.66];
  loop = {
    start: loopRange[0] * trackLength,
    end: loopRange[1] * trackLength,
  };
  loop.radius = (loop.end - loop.start) / (Math.PI * 2);
}

buildTrack(activeTrackId);

const car = {
  x: 0,
  y: 0,
  z: 0,
  angle: 0,
  s: 0,
  lateral: 0,
  speed: 0,
  steer: 0,
  yawLean: 0,
  looping: false,
  roll: 0,
};

let nextCheckpoint = 0;
let lapStart = performance.now();
let lapCompleteFlash = 0;
let last = performance.now();

function formatTime(ms) {
  if (!ms) return "--.---";
  return (ms / 1000).toFixed(3);
}

function localBestKey() {
  return `${bestKey}-${activeTrackId}`;
}

function loadLocalBest() {
  best = Number(localStorage.getItem(localBestKey())) || 0;
  bestTimeEl.textContent = formatTime(best);
}

function wrapS(s) {
  return ((s % trackLength) + trackLength) % trackLength;
}

function sampleTrackPoint(s) {
  const wrapped = wrapS(s);
  const segment = segments.find((item) => wrapped >= item.start && wrapped <= item.start + item.length) || segments[0];
  const t = (wrapped - segment.start) / segment.length;
  const x = segment.a.x + (segment.b.x - segment.a.x) * t;
  const z = segment.a.z + (segment.b.z - segment.a.z) * t;
  return { x, z };
}

function sampleTrack(s) {
  const point = sampleTrackPoint(s);
  const behind = sampleTrackPoint(s - 90);
  const ahead = sampleTrackPoint(s + 90);
  const angle = Math.atan2(ahead.z - behind.z, ahead.x - behind.x);
  const x = point.x;
  const z = point.z;
  return { x, z, angle };
}

function betweenS(s, start, end) {
  const value = wrapS(s);
  const from = wrapS(start);
  const to = wrapS(end);
  if (from <= to) return value >= from && value <= to;
  return value >= from || value <= to;
}

function trackHeight(s) {
  const value = wrapS(s);
  let height = Math.sin((value / trackLength) * Math.PI * 4.4) * 18 + Math.sin((value / trackLength) * Math.PI * 9.2) * 9 + 22;

  if (betweenS(value, loop.start, loop.end)) {
    const progress = (value - loop.start) / (loop.end - loop.start);
    height += (1 - Math.cos(progress * Math.PI * 2)) * loop.radius;
  }

  return Math.max(0, height);
}

function loopProgress(s) {
  const value = wrapS(s);
  if (!betweenS(value, loop.start, loop.end)) return null;
  return (value - loop.start) / (loop.end - loop.start);
}

function placeCarOnTrack() {
  const center = sampleTrack(car.s);
  const normal = { x: -Math.sin(center.angle), z: Math.cos(center.angle) };
  car.x = center.x + normal.x * car.lateral;
  car.z = center.z + normal.z * car.lateral;
  car.angle = center.angle;
  car.y = trackHeight(car.s);
}

function nearestTrackInfo(x, z) {
  let bestMatch = { s: 0, lateral: 0, distance: Infinity };

  segments.forEach((segment) => {
    const vx = segment.b.x - segment.a.x;
    const vz = segment.b.z - segment.a.z;
    const wx = x - segment.a.x;
    const wz = z - segment.a.z;
    const t = Math.max(0, Math.min(1, (wx * vx + wz * vz) / (segment.length * segment.length)));
    const cx = segment.a.x + vx * t;
    const cz = segment.a.z + vz * t;
    const dx = x - cx;
    const dz = z - cz;
    const distance = Math.hypot(dx, dz);
    const angle = Math.atan2(vz, vx);
    const normal = { x: -Math.sin(angle), z: Math.cos(angle) };
    const lateral = dx * normal.x + dz * normal.z;

    if (distance < bestMatch.distance) {
      bestMatch = {
        s: wrapS(segment.start + segment.length * t),
        lateral,
        distance,
      };
    }
  });

  return bestMatch;
}

function carWorld() {
  return {
    x: car.x,
    y: car.y,
    z: car.z,
    angle: car.angle + car.yawLean,
  };
}

function resetCar() {
  const spawnS = trackLength - 25;
  const start = sampleTrack(spawnS);
  car.x = start.x;
  car.y = 0;
  car.z = start.z;
  car.angle = start.angle;
  car.s = spawnS;
  car.lateral = 0;
  car.speed = 0;
  car.steer = 0;
  car.yawLean = 0;
  car.looping = false;
  car.roll = 0;
  placeCarOnTrack();
  nextCheckpoint = 0;
  lapStart = performance.now();
  messageEl.textContent = "Floor it through the green start gate.";
}

function crossedCheckpoint(previousS, currentS, targetS) {
  if (currentS >= previousS) return targetS >= previousS && targetS <= currentS;
  return targetS >= previousS || targetS <= currentS;
}

function update(dt) {
  const gas = keys.has("gas") || keys.has("w") || keys.has("arrowup");
  const brake = keys.has("brake") || keys.has("s") || keys.has("arrowdown");
  const left = keys.has("left") || keys.has("a") || keys.has("arrowleft");
  const right = keys.has("right") || keys.has("d") || keys.has("arrowright");

  if (keys.has("r")) resetCar();

  const rawTurn = (left ? 1 : 0) - (right ? 1 : 0);
  car.steer += (rawTurn - car.steer) * Math.min(1, dt * 6.5);
  const previousS = wrapS(car.s);
  const offRoad = Math.abs(car.lateral) > roadWidth * 0.52;
  const progress = loopProgress(car.s);
  car.looping = progress !== null && !offRoad;

  const grip = offRoad ? 0.5 : 1;
  if (gas) car.speed += 410 * dt * grip;
  if (brake) car.speed -= 680 * dt;

  const speedFactor = Math.min(Math.abs(car.speed) / 340, 1.15);
  const brakeAssist = brake ? 1.22 : 1;
  const turnGrip = offRoad ? 0.55 : 1;
  const turnRate = speedFactor * 1.08 * brakeAssist * turnGrip;
  car.angle += car.steer * turnRate * dt * Math.sign(car.speed || 1);

  if (car.looping) {
    const theta = progress * Math.PI * 2;
    car.speed -= 620 * Math.sin(theta) * dt;
    car.roll = theta;
    car.lateral *= Math.pow(0.88, dt * 60);
    messageEl.textContent = car.speed >= 0 ? "Physical loop: gravity is fighting you." : "Stalled on the loop. Roll back and try faster.";
  } else {
    car.roll += (0 - car.roll) * Math.min(1, dt * 8);
    if (offRoad && Math.abs(car.speed) > 90) messageEl.textContent = "Off road: lift or brake to regain grip.";
  }

  car.yawLean += (car.steer * 0.12 - car.yawLean) * Math.min(1, dt * 7);
  car.speed *= Math.pow(offRoad ? 0.955 : 0.987, dt * 60);
  if (offRoad && car.speed > 300) car.speed -= (car.speed - 300) * Math.min(1, dt * 1.7);
  car.speed = Math.max(Math.min(car.speed, 760), -250);
  car.x += Math.cos(car.angle) * car.speed * dt;
  car.z += Math.sin(car.angle) * car.speed * dt;

  const trackInfo = nearestTrackInfo(car.x, car.z);
  car.s = trackInfo.s;
  car.lateral = trackInfo.lateral;
  car.y = trackHeight(car.s);

  const afterProgress = loopProgress(car.s);
  if (afterProgress !== null && !offRoad) {
    const theta = afterProgress * Math.PI * 2;
    const lacksCentripetalForce = Math.cos(theta) < -0.2 && car.speed * car.speed < loop.radius * 620 * 0.82;
    if (lacksCentripetalForce) {
      car.speed = Math.min(car.speed, 35);
      messageEl.textContent = "Not enough speed to stay on the loop.";
    }
  }

  const currentS = wrapS(car.s);
  const checkpoint = checkpoints[nextCheckpoint];

  if (car.speed >= 0 && crossedCheckpoint(previousS, currentS, checkpoint.s)) {
    if (nextCheckpoint === 0) lapStart = performance.now();
    nextCheckpoint += 1;
    if (nextCheckpoint >= checkpoints.length) {
      const lap = performance.now() - lapStart;
      if (!best || lap < best) {
        best = lap;
        localStorage.setItem(localBestKey(), String(best));
        messageEl.textContent = `New best: ${formatTime(lap)} seconds.`;
      } else {
        messageEl.textContent = `Lap complete: ${formatTime(lap)} seconds.`;
      }
      submitLap(lap);
      lapCompleteFlash = 1;
      nextCheckpoint = 0;
      lapStart = performance.now();
    } else {
      messageEl.textContent = `Hit ${checkpoint.label}. Next: ${checkpoints[nextCheckpoint].label}.`;
    }
  }

  lapCompleteFlash = Math.max(0, lapCompleteFlash - dt * 1.8);
  lapTimeEl.textContent = formatTime(performance.now() - lapStart);
  bestTimeEl.textContent = formatTime(best);
  checkpointEl.textContent = `${nextCheckpoint + 1}/${checkpoints.length}`;
}

function project(world, camera) {
  const dx = world.x - camera.x;
  const dz = world.z - camera.z;
  const sin = Math.sin(-camera.angle + Math.PI / 2);
  const cos = Math.cos(-camera.angle + Math.PI / 2);
  const x = dx * cos - dz * sin;
  const z = dx * sin + dz * cos;
  if (z < 6) return null;
  return {
    x: canvas.width / 2 + (x / z) * focalLength,
    y: horizon + ((cameraHeight + camera.y - (world.y || 0)) / z) * focalLength,
    scale: focalLength / z,
    z,
  };
}

function drawSkyAndGround() {
  const sky = ctx.createLinearGradient(0, 0, 0, horizon + 70);
  sky.addColorStop(0, "#24365c");
  sky.addColorStop(0.62, "#ef8f56");
  sky.addColorStop(1, "#ffe1a8");
  ctx.fillStyle = sky;
  ctx.fillRect(-canvas.width, -canvas.height, canvas.width * 3, horizon + canvas.height + 90);

  const ground = ctx.createLinearGradient(0, horizon, 0, canvas.height);
  ground.addColorStop(0, "#47552c");
  ground.addColorStop(1, "#172011");
  ctx.fillStyle = ground;
  ctx.fillRect(-canvas.width, horizon, canvas.width * 3, canvas.height * 2);
}

function drawMountains() {
  ctx.fillStyle = "rgba(31, 39, 55, 0.72)";
  ctx.beginPath();
  ctx.moveTo(0, horizon + 34);
  for (let x = 0; x <= canvas.width; x += 110) {
    ctx.lineTo(x + 42, horizon - 70 - Math.sin(x * 0.013) * 34);
    ctx.lineTo(x + 110, horizon + 34);
  }
  ctx.lineTo(canvas.width, horizon + 80);
  ctx.lineTo(0, horizon + 80);
  ctx.fill();
}

function roadEdgeAt(s, lateral) {
  const center = sampleTrack(s);
  const normal = { x: -Math.sin(center.angle), z: Math.cos(center.angle) };
  return { x: center.x + normal.x * lateral, y: trackHeight(s), z: center.z + normal.z * lateral };
}

function drawRoad(camera) {
  const slices = [];
  for (let depth = 18; depth <= 1850; depth += 26 + depth * 0.018) {
    const s = car.s + depth;
    const left = project(roadEdgeAt(s, -roadWidth / 2), camera);
    const right = project(roadEdgeAt(s, roadWidth / 2), camera);
    if (left && right) slices.push({ left, right, s });
  }

  for (let i = slices.length - 2; i >= 0; i -= 1) {
    const near = slices[i];
    const far = slices[i + 1];
    const stripe = Math.floor(near.s / 90) % 2;
    const isLoop = betweenS(near.s, loop.start, loop.end);
    ctx.fillStyle = isLoop
      ? stripe
        ? "#5d36d9"
        : "#7c4dff"
        : stripe
          ? "#303840"
          : "#283038";
    ctx.beginPath();
    ctx.moveTo(near.left.x, near.left.y);
    ctx.lineTo(near.right.x, near.right.y);
    ctx.lineTo(far.right.x, far.right.y);
    ctx.lineTo(far.left.x, far.left.y);
    ctx.closePath();
    ctx.fill();

    ctx.strokeStyle = "rgba(255,255,255,0.34)";
    ctx.lineWidth = Math.max(1, near.left.scale * 0.8);
    ctx.beginPath();
    ctx.moveTo(near.left.x, near.left.y);
    ctx.lineTo(far.left.x, far.left.y);
    ctx.moveTo(near.right.x, near.right.y);
    ctx.lineTo(far.right.x, far.right.y);
    ctx.stroke();
  }
}

function drawCheckpoints(camera) {
  checkpoints.forEach((checkpoint, index) => {
    const distance = wrapS(checkpoint.s - car.s);
    if (distance < 12 || distance > 1250) return;
    const leftEdge = roadEdgeAt(checkpoint.s, -roadWidth * 0.6);
    const rightEdge = roadEdgeAt(checkpoint.s, roadWidth * 0.6);
    const left = project(leftEdge, camera);
    const right = project(rightEdge, camera);
    const topLeft = project({ ...leftEdge, y: leftEdge.y + 115 }, camera);
    const topRight = project({ ...rightEdge, y: rightEdge.y + 115 }, camera);
    if (!left || !right || !topLeft || !topRight) return;
    const active = index === nextCheckpoint;
    ctx.strokeStyle = active ? "#64ff9a" : "rgba(255,255,255,0.34)";
    ctx.lineWidth = active ? 7 : 3;
    ctx.beginPath();
    ctx.moveTo(left.x, left.y);
    ctx.lineTo(topLeft.x, topLeft.y);
    ctx.lineTo(topRight.x, topRight.y);
    ctx.lineTo(right.x, right.y);
    ctx.stroke();
  });
}

function drawLoopGates(camera) {
  for (let i = 1; i <= 4; i += 1) {
    const s = loop.start + ((loop.end - loop.start) * i) / 5;
    const distance = wrapS(s - car.s);
    if (distance < 12 || distance > 1250) continue;

    const leftEdge = roadEdgeAt(s, -roadWidth * 0.72);
    const rightEdge = roadEdgeAt(s, roadWidth * 0.72);
    const top = roadEdgeAt(s, 0);
    top.y += 165;

    const left = project(leftEdge, camera);
    const right = project(rightEdge, camera);
    const topPoint = project(top, camera);
    if (!left || !right || !topPoint) continue;

    ctx.strokeStyle = "rgba(188, 168, 255, 0.78)";
    ctx.lineWidth = Math.max(2, left.scale * 0.7);
    ctx.beginPath();
    ctx.moveTo(left.x, left.y);
    ctx.quadraticCurveTo(topPoint.x, topPoint.y, right.x, right.y);
    ctx.stroke();
  }
}

function drawCockpit() {
  ctx.fillStyle = "rgba(5, 7, 10, 0.8)";
  ctx.beginPath();
  ctx.ellipse(canvas.width / 2, canvas.height + 90, 380, 150, 0, Math.PI, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255, 107, 25, 0.95)";
  ctx.lineWidth = 8;
  ctx.beginPath();
  ctx.arc(canvas.width / 2, canvas.height - 6, 86, Math.PI * 1.08, Math.PI * 1.92);
  ctx.stroke();

  const speedText = `${Math.abs(Math.round(car.speed))} km/h`;
  ctx.fillStyle = "#f7fbff";
  ctx.font = "800 24px ui-sans-serif, system-ui";
  ctx.textAlign = "center";
  ctx.fillText(speedText, canvas.width / 2, canvas.height - 28);

  if (car.looping) {
    ctx.fillStyle = "#bca8ff";
    ctx.font = "900 18px ui-sans-serif, system-ui";
    ctx.fillText("LOOP", canvas.width / 2, canvas.height - 62);
  }
}

function renderLeaderboard(scores) {
  if (!scores.length) {
    leaderboardListEl.innerHTML = "<li>No laps yet. Set the first time.</li>";
    return;
  }

  leaderboardListEl.innerHTML = scores
    .map((score) => `<li><strong>${escapeHtml(score.name)}</strong> ${formatTime(score.time)}</li>`)
    .join("");
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"]/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
  })[char]);
}

async function loadLeaderboard() {
  leaderboardListEl.innerHTML = "<li>Global leaderboard is temporarily disabled. Local best times still work.</li>";
}

async function submitLap(lap) {
  leaderboardListEl.innerHTML = `<li>Leaderboard disabled. Last completed lap: ${formatTime(lap)}.</li>`;
}

function draw() {
  const camera = carWorld();
  ctx.save();
  ctx.translate(canvas.width / 2, canvas.height / 2);
  ctx.rotate(-car.roll);
  ctx.translate(-canvas.width / 2, -canvas.height / 2);
  drawSkyAndGround();
  drawMountains();
  drawRoad(camera);
  drawLoopGates(camera);
  drawCheckpoints(camera);
  if (lapCompleteFlash > 0) {
    ctx.fillStyle = `rgba(100,255,154,${lapCompleteFlash * 0.22})`;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }
  drawCockpit();
  ctx.restore();
}

function frame(now) {
  const dt = Math.min((now - last) / 1000, 0.04);
  last = now;
  update(dt);
  draw();
  requestAnimationFrame(frame);
}

const controlKeys = new Set(["arrowup", "arrowdown", "arrowleft", "arrowright", "w", "a", "s", "d", "r"]);

addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if (controlKeys.has(key)) event.preventDefault();
  keys.add(key);
});

addEventListener("keyup", (event) => {
  const key = event.key.toLowerCase();
  if (controlKeys.has(key)) event.preventDefault();
  keys.delete(key);
});

document.querySelectorAll(".touch button").forEach((button) => {
  const key = button.dataset.key;
  const activePointers = new Set();

  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture(event.pointerId);
    activePointers.add(event.pointerId);
    button.classList.add("active");
    keys.add(key);
  });

  function releasePointer(event) {
    event.preventDefault();
    activePointers.delete(event.pointerId);
    if (activePointers.size === 0) {
      button.classList.remove("active");
      keys.delete(key);
    }
  }

  button.addEventListener("pointerup", releasePointer);
  button.addEventListener("pointercancel", releasePointer);
  button.addEventListener("lostpointercapture", releasePointer);
});

driverNameEl.value = localStorage.getItem(driverKey) || "";
driverForm.addEventListener("submit", (event) => {
  event.preventDefault();
  localStorage.setItem(driverKey, driverNameEl.value.trim().slice(0, 18));
  messageEl.textContent = "Driver name saved.";
});

trackSelectEl.value = activeTrackId;
trackSelectEl.addEventListener("change", () => {
  buildTrack(trackSelectEl.value);
  loadLocalBest();
  resetCar();
  messageEl.textContent = `${activeTrack.name} loaded.`;
});

loadLocalBest();
resetCar();
loadLeaderboard();
requestAnimationFrame(frame);
