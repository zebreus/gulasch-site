(function () {
  "use strict";

  const root = document.documentElement;
  const body = document.body;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduceMotion) return;

  // --------------------------------------------------
  // 1. DIGITAL RAIN
  // --------------------------------------------------
  const rainCanvas = document.createElement("canvas");
  rainCanvas.id = "rainCanvas";
  rainCanvas.setAttribute("aria-hidden", "true");
  body.prepend(rainCanvas);

  const ctx = rainCanvas.getContext("2d");
  const chars = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF<>/{}[]|&^%$#@!";
  const drops = [];
  let rainW, rainH;

  function resizeRain() {
    rainW = rainCanvas.width = window.innerWidth;
    rainH = rainCanvas.height = window.innerHeight;
    drops.length = 0;
    const count = Math.min(140, Math.floor(rainW / 8));
    for (let i = 0; i < count; i++) {
      drops.push({
        x: Math.random() * rainW,
        y: Math.random() * rainH * -1,
        speed: 2 + Math.random() * 5,
        len: 8 + Math.floor(Math.random() * 16),
        opacity: 0.08 + Math.random() * 0.16,
      });
    }
  }
  resizeRain();
  window.addEventListener("resize", resizeRain, { passive: true });

  function drawRain() {
    const chaos = Number.parseFloat(getComputedStyle(root).getPropertyValue("--editor-chaos")) || 1;
    ctx.clearRect(0, 0, rainW, rainH);
    for (const drop of drops) {
      const char = chars[Math.floor(Math.random() * chars.length)];
      const baseOpacity = drop.opacity * Math.min(1, chaos * 0.8);
      for (let i = 0; i < drop.len; i++) {
        const yPos = drop.y - i * 14;
        if (yPos < 0 || yPos > rainH) continue;
        const fade = 1 - i / drop.len;
        ctx.fillStyle = `rgba(72, 255, 153, ${baseOpacity * fade * fade})`;
        ctx.font = `${13 + chaos * 2}px monospace`;
        ctx.fillText(char, drop.x, yPos);
      }
      drop.y += drop.speed * chaos * 0.7;
      if (drop.y - drop.len * 14 > rainH) {
        drop.y = -Math.random() * rainH * 0.5;
        drop.x = Math.random() * rainW;
        drop.speed = 2 + Math.random() * 5;
      }
    }
  }

  // --------------------------------------------------
  // 2. TERMINAL OPS FEED
  // --------------------------------------------------
  const terminal = document.querySelector(".terminal");
  let feedContainer;

  if (terminal) {
    feedContainer = document.createElement("div");
    feedContainer.className = "terminal-feed";
    feedContainer.setAttribute("aria-hidden", "true");
    const radar = terminal.querySelector(".radar");
    if (radar) {
      terminal.insertBefore(feedContainer, radar);
    } else {
      terminal.appendChild(feedContainer);
    }

    const opsLogs = [
      "[INF] Wheel revolutions: 2,418 — all quiet",
      "[WRN] Water bottle below 30% — refill scheduled",
      "[INF] Bedding change due in 2 days",
      "[ERR] Hamster spotted chewing cable management",
      "[INF] UV-B lamp hours: 1,234 / 3,000",
      "[WRN] Parrot screeches logged: 47 (3-min avg)",
      "[INF] Treats dispensed: 6 sunflower, 2 pumpkin",
      "[ERR] Suspicious noise from nesting box — resolved",
      "[INF] Ambient temperature 22.4°C, humidity 48%",
      "[WRN] Resident climbing curtain — refraining from intervention",
      "[INF] Snack inventory: pumpkin running low",
      "[ERR] Door latch detected at 78% integrity — tightening scheduled",
      "[INF] Daily enrichment score: 9.2 / 10",
      "[WRN] Feather molt detected — extra protein supplied",
      "[INF] Curiosity index: elevated",
      "[ERR] Curious inspection by feline neighbor — logged",
      "[INF] Nap cycle complete — resident active",
      "[WRN] Treat dispenser jammed — manual refill",
      "[INF] Cage humidity 48% — stable",
      "[ERR] Minor escape attempt in cage-07 — secured",
      "[INF] Mood: 'alert but approachable'",
      "[WRN] Basking spot requested +1°C in reptile wing",
      "[INF] UV-B cycle running nominal",
      "[ERR] Stranger (human) in room — alarm bark logged",
      "[INF] Wheel: silent. Resident: proud.",
    ];

    function addLogEntry() {
      const entry = document.createElement("p");
      entry.textContent = opsLogs[Math.floor(Math.random() * opsLogs.length)];
      feedContainer.appendChild(entry);
      const max = 14;
      while (feedContainer.children.length > max) {
        feedContainer.removeChild(feedContainer.firstChild);
      }
      feedContainer.scrollTop = feedContainer.scrollHeight;
    }

    // Prime with entries
    for (let i = 0; i < 6; i++) addLogEntry();
    setInterval(addLogEntry, 2200 + Math.random() * 1800);
  }

  // --------------------------------------------------
  // 3. TYPEWRITER EFFECT ON LEAD
  // --------------------------------------------------
  const leadEl = document.querySelector(".lead");
  if (leadEl) {
    const fullText = leadEl.textContent;
    leadEl.textContent = "";
    leadEl.style.visibility = "visible";
    let idx = 0;
    const speed = 18;

    function typeChar() {
      if (idx < fullText.length) {
        leadEl.textContent += fullText[idx];
        idx++;
        const delay = fullText[idx - 1] === "." ? speed * 8 : fullText[idx - 1] === "," ? speed * 4 : speed;
        setTimeout(typeChar, delay + Math.random() * 10);
      } else {
        leadEl.classList.add("done");
      }
    }
    setTimeout(typeChar, 400);
  }

  // --------------------------------------------------
  // 4. SCROLL REVEAL
  // --------------------------------------------------
  const revealSections = document.querySelectorAll(
    "#mission, #build, #pets, #stats, #purrs, #signals, #contact, .showcase"
  );
  revealSections.forEach((el) => el.classList.add("reveal"));

  const revealObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add("revealed");
        }
      }
    },
    { threshold: 0.18, rootMargin: "0px 0px -40px 0px" }
  );
  revealSections.forEach((el) => revealObserver.observe(el));

  // --------------------------------------------------
  // 5. MOUSE GLOW TRAIL
  // --------------------------------------------------
  const glow = document.createElement("div");
  glow.className = "mouse-glow";
  glow.setAttribute("aria-hidden", "true");
  body.appendChild(glow);

  let glowX = -200,
    glowY = -200;
  document.addEventListener(
    "pointermove",
    (e) => {
      glowX = e.clientX;
      glowY = e.clientY;
    },
    { passive: true }
  );

  let glowRAF = 0;
  function animateGlow() {
    const chaos = Number.parseFloat(getComputedStyle(root).getPropertyValue("--editor-chaos")) || 1;
    const size = 120 + chaos * 80;
    const hue = ((Date.now() * 0.05 * chaos) % 360);
    glow.style.background = `radial-gradient(circle ${size}px at ${glowX}px ${glowY}px, hsla(${hue}, 100%, 68%, ${0.08 + chaos * 0.04}), transparent 80%)`;
    glowRAF = requestAnimationFrame(animateGlow);
  }
  animateGlow();

  // --------------------------------------------------
  // 6. KONAMI CODE EASTER EGG
  // --------------------------------------------------
  const konami = [
    "ArrowUp", "ArrowUp", "ArrowDown", "ArrowDown",
    "ArrowLeft", "ArrowRight", "ArrowLeft", "ArrowRight",
    "b", "a",
  ];
  let konamiIdx = 0;
  let konamiActive = false;

  document.addEventListener("keydown", (e) => {
    if (konamiActive) return;
    if (e.key === konami[konamiIdx]) {
      konamiIdx++;
      if (konamiIdx === konami.length) {
        konamiActive = true;
        triggerKonami();
        konamiIdx = 0;
      }
    } else {
      konamiIdx = 0;
    }
  });

  function triggerKonami() {
    root.style.setProperty("--editor-chaos", "3");
    body.dataset.chaos = "max";

    const banner = document.createElement("div");
    banner.className = "live-banner konami-banner";
    banner.textContent = "⚡ KONAMI MODE ACTIVATED ⚡ MAXIMUM CHAOS";
    banner.style.background = "linear-gradient(90deg, #ff5577, #ffc75a, #48ff99, #60d8ff, #b695ff)";
    banner.style.color = "#000";
    banner.style.fontWeight = "950";
    banner.style.boxShadow = "0 0 80px rgba(255, 85, 119, 0.6)";
    document.body.appendChild(banner);

    sayTerminal("╔════ KONAMI MODE ════╗");
    sayTerminal("║   MAXIMUM CHAOS     ║");
    sayTerminal("║   ALL PETS UNLEASHED║");
    sayTerminal("╚═════════════════════╝");

    // Cycle hues
    const hues = ["red", "amber", "green", "blue", "purple"];
    let hi = 0;
    setInterval(() => {
      const editor = document.querySelector('[data-editor-action="reset"]');
      if (!editor) return;
      const hue = hues[hi % hues.length];
      hi++;
      const themeMap = {
        red: ["#ff4d6d", "#ffb000", "#48ff99", "#60d8ff", "#ff7ab6"],
        amber: ["#ffc75a", "#ff8c42", "#48ff99", "#ff5577", "#fde68a"],
        green: ["#48ff99", "#60d8ff", "#ffc75a", "#ff5577", "#b695ff"],
        blue: ["#60d8ff", "#48ff99", "#b695ff", "#ff5577", "#7dd3fc"],
        purple: ["#b695ff", "#60d8ff", "#ffc75a", "#ff5577", "#f0abfc"],
      };
      const theme = themeMap[hue];
      ["--green", "--cyan", "--yellow", "--red", "--violet"].forEach((key, i) => root.style.setProperty(key, theme[i]));
    }, 1200);
  }

  function sayTerminal(text) {
    if (!feedContainer) return;
    const p = document.createElement("p");
    p.textContent = text;
    p.style.color = "#ff5577";
    p.style.fontWeight = "900";
    feedContainer.appendChild(p);
    feedContainer.scrollTop = feedContainer.scrollHeight;
  }

  // --------------------------------------------------
  // 7. WEB AUDIO AMBIENT
  // --------------------------------------------------
  let audioCtx = null;

  function initAudio() {
    if (audioCtx) return;
    try {
      audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();

      // Subtle low drone
      const osc = audioCtx.createOscillator();
      osc.type = "sine";
      osc.frequency.value = 52;

      const sub = audioCtx.createOscillator();
      sub.type = "sine";
      sub.frequency.value = 38;

      const gain = audioCtx.createGain();
      gain.gain.value = 0.035;
      const subGain = audioCtx.createGain();
      subGain.gain.value = 0.025;

      const filter = audioCtx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 160;

      osc.connect(gain).connect(filter).connect(audioCtx.destination);
      sub.connect(subGain).connect(filter);
      osc.start();
      sub.start();

      // Random beeps
      function beep() {
        if (!audioCtx || document.hidden) {
          setTimeout(beep, 2000 + Math.random() * 3000);
          return;
        }
        const bOsc = audioCtx.createOscillator();
        bOsc.type = "sine";
        bOsc.frequency.value = 400 + Math.random() * 800;

        const bGain = audioCtx.createGain();
        bGain.gain.setValueAtTime(0, audioCtx.currentTime);
        bGain.gain.linearRampToValueAtTime(0.012, audioCtx.currentTime + 0.01);
        bGain.gain.linearRampToValueAtTime(0, audioCtx.currentTime + 0.06 + Math.random() * 0.08);

        bOsc.connect(bGain).connect(audioCtx.destination);
        bOsc.start();
        bOsc.stop(audioCtx.currentTime + 0.1);

        const chaos = Number.parseFloat(getComputedStyle(root).getPropertyValue("--editor-chaos")) || 1;
        const delay = 1200 + Math.random() * 2800 / Math.max(0.25, chaos);
        setTimeout(beep, delay);
      }
      setTimeout(beep, 3000);
    } catch {
      // Audio not available, silently skip
    }
  }

  // Init audio on first user interaction
  const initEvents = ["click", "touchstart", "keydown"];
  function bootAudio() {
    initAudio();
    initEvents.forEach((ev) => document.removeEventListener(ev, bootAudio));
  }
  initEvents.forEach((ev) => document.addEventListener(ev, bootAudio, { once: false, passive: true }));

  // --------------------------------------------------
  // ANIMATION LOOP
  // --------------------------------------------------
  let rainRAF = 0;

  function mainLoop() {
    drawRain();
    rainRAF = requestAnimationFrame(mainLoop);
  }
  mainLoop();

  // Listen for chaos changes from the editor — update rain style
  const chaosObserver = new MutationObserver(() => {
    const c = root.style.getPropertyValue("--editor-chaos");
    rainCanvas.style.opacity = Math.min(0.35, 0.12 + c * 0.08);
  });
  chaosObserver.observe(root, { attributes: true, attributeFilter: ["style"] });

  // --------------------------------------------------
  // TIME-OF-DAY TOGGLE
  // --------------------------------------------------
  const timeToggle = document.querySelector("[data-time-toggle]");
  if (timeToggle) {
    timeToggle.addEventListener("click", () => {
      const isNight = body.dataset.time === "night";
      const next = isNight ? "day" : "night";
      if (window.c3cockEditor?.setTime) {
        window.c3cockEditor.setTime(next);
        return;
      }
      body.dataset.time = next;
      const label = timeToggle.querySelector(".time-label");
      const icon = timeToggle.querySelector(".time-icon");
      if (label) label.textContent = next === "night" ? "Night" : "Day";
      if (icon) icon.textContent = next === "night" ? "Sun" : "Moon";
      timeToggle.setAttribute("aria-pressed", String(next === "night"));
    });
  }

  // --------------------------------------------------
  // PET CARD PICKER
  // --------------------------------------------------
  const petCards = document.querySelectorAll(".pet-card");
  const petProfile = {
    hamster:  { label: "Syrian hamster",       size: "100 × 50 cm",  mood: "whisker-twitchy",  wheel: true,  wheelRevs: 2418 },
    parrot:   { label: "Cockatiel",            size: "120 × 80 cm",  mood: "judging",          wheel: false, wheelRevs: 0 },
    reptile:  { label: "Bearded dragon",       size: "90 × 45 cm",   mood: "toasty",           wheel: false, wheelRevs: 0 },
    rabbit:   { label: "Holland lop",          size: "150 × 80 cm",  mood: "flop-prone",       wheel: false, wheelRevs: 0 },
    fish:     { label: "Betta community",      size: "30 L tank",    mood: "bubbly",           wheel: false, wheelRevs: 0 },
    ferret:   { label: "Mischief of ferrets",  size: "140 × 70 cm",  mood: "chaotic",          wheel: false, wheelRevs: 0 },
  };

  petCards.forEach((card) => {
    card.addEventListener("click", () => {
      petCards.forEach((c) => {
        c.classList.remove("is-active");
        c.setAttribute("aria-checked", "false");
      });
      card.classList.add("is-active");
      card.setAttribute("aria-checked", "true");
      const pet = card.dataset.pet;
      const profile = petProfile[pet];
      if (!profile) return;

      const petEl = document.querySelector('[data-live="pet"]');
      const moodEl = document.querySelector('[data-live="mood"]');
      const wheelStat = document.querySelector('[data-stat="wheel"]');
      if (petEl) petEl.textContent = profile.label;
      if (moodEl) moodEl.textContent = profile.mood;
      if (wheelStat) wheelStat.textContent = profile.wheelRevs.toLocaleString();

      // Add a terminal entry about the new pet
      if (feedContainer) {
        const entry = document.createElement("p");
        entry.textContent = `[INF] Resident switched: now housing ${profile.label}`;
        entry.style.color = "#9affc0";
        feedContainer.appendChild(entry);
        feedContainer.scrollTop = feedContainer.scrollHeight;
      }
    });
  });

  // --------------------------------------------------
  // QUOTE FORM
  // --------------------------------------------------
  const quoteForm = document.querySelector("#quoteForm");
  if (quoteForm) {
    quoteForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const out = quoteForm.querySelector("output");
      if (out) {
        out.textContent = "Quoted. Check your inbox in about 24 hours.";
        out.classList.add("is-shown");
      }
    });
  }

  // --------------------------------------------------
  // LIVE STATS UPDATER
  // --------------------------------------------------
  const statWheel = document.querySelector('[data-stat="wheel"]');
  const statWater = document.querySelector('[data-stat="water"]');
  const statUvb = document.querySelector('[data-stat="uvb"]');
  const statMood = document.querySelector('[data-stat="mood"]');
  const statMoodNote = document.querySelector('[data-stat="mood-note"]');
  const moodLabels = ["curious", "snack-focused", "alert", "cautious", "dozy", "whisker-twitchy", "judging", "flop-prone", "toasty", "bubbly"];

  if (statWheel) {
    let revs = 2418;
    setInterval(() => {
      revs += Math.floor(Math.random() * 6) + 1;
      statWheel.textContent = revs.toLocaleString();
    }, 1500 + Math.random() * 1000);
  }

  if (statWater) {
    let water = 92;
    setInterval(() => {
      if (Math.random() < 0.3) {
        water = Math.max(18, water - Math.floor(Math.random() * 4));
      } else if (Math.random() < 0.2) {
        water = Math.min(100, water + Math.floor(Math.random() * 8));
      }
      statWater.textContent = `${water}%`;
    }, 2500);
  }

  if (statUvb) {
    let uvb = 1766;
    setInterval(() => {
      uvb = Math.max(0, uvb - 1);
      statUvb.textContent = uvb.toLocaleString();
    }, 4000);
  }

  if (statMood) {
    let score = 8.4;
    setInterval(() => {
      score = Math.max(2, Math.min(10, score + (Math.random() - 0.45) * 0.4));
      statMood.textContent = score.toFixed(1);
      if (statMoodNote) {
        const lbl = moodLabels[Math.floor(Math.random() * moodLabels.length)];
        statMoodNote.textContent = `state: ${lbl}`;
      }
    }, 3000);
  }

  // --------------------------------------------------
  // CLICK-TO-FEED (clicking the hero stage gives a snack)
  // --------------------------------------------------
  const stage = document.querySelector(".hero-stage");
  if (stage) {
    stage.style.cursor = "pointer";
    stage.addEventListener("click", (e) => {
      // Create a little heart/treat at click position
      const treat = document.createElement("span");
      treat.className = "floating-treat";
      treat.textContent = ["🌱", "🌻", "🍎", "🥜", "🥕"][Math.floor(Math.random() * 5)];
      const rect = stage.getBoundingClientRect();
      treat.style.left = `${e.clientX - rect.left}px`;
      treat.style.top = `${e.clientY - rect.top}px`;
      stage.appendChild(treat);
      setTimeout(() => treat.remove(), 1400);

      // Add terminal entry
      if (feedContainer) {
        const entry = document.createElement("p");
        entry.textContent = "[INF] Treat dispensed at hero stage";
        entry.style.color = "#ffd9a3";
        feedContainer.appendChild(entry);
        feedContainer.scrollTop = feedContainer.scrollHeight;
      }

      // Boost mood
      if (statMood) {
        const cur = parseFloat(statMood.textContent) || 8;
        const next = Math.min(10, cur + 0.3);
        statMood.textContent = next.toFixed(1);
      }
    });
  }
})();
