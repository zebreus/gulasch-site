(function () {
  const root = document.documentElement;
  const panel = document.querySelector(".chat-editor");
  const toggle = document.querySelector(".chat-toggle");
  const log = document.querySelector("#chatLog");
  const form = document.querySelector("#chatForm");
  const input = document.querySelector("#chatInput");
  const reset = document.querySelector('[data-editor-action="reset"]');
  const storageKey = "c3cock-live-editor-state";

  if (!panel || !toggle || !log || !form || !input) return;

  const defaults = {
    title: "Cages your pet actually likes.",
    lead: "Modular, hand-finished habitats for hamsters, parrots, reptiles, and the small mammals that own the house. Designed around the animal inside, not just the room outside. Built in Karlsruhe. Shipped to wherever the pet is.",
    banner: "",
    chaos: 1,
    hue: "green",
    time: "day",
  };

  const embeddedState = {
    ...defaults,
    updatedAt: "static-build",
  };

  let state = { ...defaults };
  let lastSeenUpdatedAt = "";
  let saving = false;
  let warnedOffline = false;

  function stripMeta(value) {
    return {
      title: value.title,
      lead: value.lead,
      banner: value.banner,
      chaos: value.chaos,
      hue: value.hue,
      time: value.time,
    };
  }

  function loadLocalState() {
    try {
      return { ...defaults, ...JSON.parse(localStorage.getItem(storageKey) || "{}") };
    } catch {
      return { ...defaults };
    }
  }

  function saveLocalState(value) {
    try {
      localStorage.setItem(storageKey, JSON.stringify(stripMeta(value)));
    } catch {
      // Ignore private browsing or disabled storage.
    }
  }

  async function loadSharedState() {
    return { ...embeddedState, ...loadLocalState() };
  }

  async function saveSharedState() {
    saving = true;
    try {
      state = { ...defaults, ...stripMeta(state), updatedAt: new Date().toISOString() };
      lastSeenUpdatedAt = state.updatedAt;
      saveLocalState(state);
      warnedOffline = false;
      return true;
    } catch {
      saveLocalState(state);
      if (!warnedOffline) {
        say("bot", "Shared save failed; keeping this change locally until the API is back.");
        warnedOffline = true;
      }
      return false;
    } finally {
      saving = false;
    }
  }

  function say(role, text) {
    const message = document.createElement("p");
    message.className = `chat-message ${role}`;
    message.textContent = text;
    log.append(message);
    log.scrollTop = log.scrollHeight;
  }

  function setText(selector, text) {
    const element = document.querySelector(selector);
    if (!element || !text) return;
    element.textContent = text;
    if (element.matches("h1")) element.dataset.text = text;
  }

  function applyHue(name) {
    const themes = {
      green: ["#48ff99", "#60d8ff", "#ffc75a", "#ff5577", "#b695ff"],
      red: ["#ff4d6d", "#ffb000", "#48ff99", "#60d8ff", "#ff7ab6"],
      blue: ["#60d8ff", "#48ff99", "#b695ff", "#ff5577", "#7dd3fc"],
      purple: ["#b695ff", "#60d8ff", "#ffc75a", "#ff5577", "#f0abfc"],
      amber: ["#ffc75a", "#ff8c42", "#48ff99", "#ff5577", "#fde68a"],
    };
    const theme = themes[name] || themes.green;
    ["--green", "--cyan", "--yellow", "--red", "--violet"].forEach((key, index) => root.style.setProperty(key, theme[index]));
  }

  function ensureBanner() {
    let banner = document.querySelector(".live-banner:not(.konami-banner)");
    if (!banner) {
      banner = document.createElement("div");
      banner.className = "live-banner";
      document.body.append(banner);
    }
    return banner;
  }

  function applyState() {
    setText("h1", state.title);
    setText(".lead", state.lead);
    root.style.setProperty("--editor-chaos", state.chaos);
    document.body.dataset.chaos = state.chaos > 1.7 ? "max" : state.chaos < 0.7 ? "calm" : "normal";
    document.body.dataset.time = state.time || "day";

    const timeToggle = document.querySelector("[data-time-toggle]");
    if (timeToggle) {
      const isNight = state.time === "night";
      timeToggle.setAttribute("aria-pressed", String(isNight));
      const label = timeToggle.querySelector(".time-label");
      const icon = timeToggle.querySelector(".time-icon");
      if (label) label.textContent = isNight ? "Night" : "Day";
      if (icon) icon.textContent = isNight ? "Sun" : "Moon";
    }

    applyHue(state.hue);

    const banner = ensureBanner();
    banner.textContent = state.banner;
    banner.hidden = !state.banner;
  }

  function extractAfter(text, words) {
    for (const word of words) {
      const index = text.toLowerCase().indexOf(word);
      if (index !== -1) return text.slice(index + word.length).trim().replace(/^[:=-]+\s*/, "");
    }
    return "";
  }

  async function persistAndReport(changes) {
    applyState();
    const shared = await saveSharedState();
    say("bot", `Applied: ${[...new Set(changes)].join(", ")}. ${shared ? "Saved locally." : "Saved locally only."}`);
  }

  async function applyPrompt(raw) {
    const prompt = raw.trim();
    const text = prompt.toLowerCase();
    const changes = [];

    if (!prompt) return;
    say("user", prompt);

    if (text.includes("reset")) {
      state = { ...defaults };
      changes.push("reset the page to defaults");
    }

    const title = extractAfter(prompt, ["title ", "headline ", "h1 "]);
    if (title) {
      state.title = title;
      changes.push("changed the headline");
    }

    const lead = extractAfter(prompt, ["lead ", "subtitle ", "description "]);
    if (lead) {
      state.lead = lead;
      changes.push("changed the intro text");
    }

    const banner = extractAfter(prompt, ["banner ", "alert ", "announcement "]);
    if (banner) {
      state.banner = banner;
      changes.push("added a live banner");
    }

    if (text.includes("hide banner") || text.includes("remove banner")) {
      state.banner = "";
      changes.push("removed the banner");
    }

    if (text.includes("chaos") || text.includes("crazy") || text.includes("insane") || text.includes("more animation")) {
      state.chaos = Math.min(3, Number(state.chaos || defaults.chaos) + 0.65);
      changes.push("increased animation intensity");
    }

    if (text.includes("calm") || text.includes("less") || text.includes("quiet")) {
      state.chaos = Math.max(0.25, Number(state.chaos || defaults.chaos) - 0.75);
      changes.push("reduced animation intensity");
    }

    if (text.includes("matrix") || text.includes("green")) state.hue = "green";
    if (text.includes("red") || text.includes("alarm") || text.includes("incident")) state.hue = "red";
    if (text.includes("blue") || text.includes("ice")) state.hue = "blue";
    if (text.includes("purple") || text.includes("violet")) state.hue = "purple";
    if (text.includes("amber") || text.includes("orange") || text.includes("gold")) state.hue = "amber";

    if (text.includes("night mode") || text.includes("dark mode") || text.includes(" bedtime") || text.includes("lights off")) {
      state.time = "night";
      changes.push("switched the cage to night cycle");
    }

    if (text.includes("day mode") || text.includes("lights on") || text.includes(" morning") || text.includes("sunrise")) {
      state.time = "day";
      changes.push("switched the cage to day cycle");
    }

    if (["green", "red", "blue", "purple", "amber"].some((color) => text.includes(color)) || text.includes("matrix") || text.includes("alarm")) {
      changes.push(`switched theme to ${state.hue}`);
    }

    if (!changes.length) {
      state.banner = prompt;
      state.chaos = Math.min(3, Number(state.chaos || defaults.chaos) + 0.2);
      changes.push("posted your text as a live banner");
    }

    await persistAndReport(changes);
  }

  async function setSharedPatch(patch, label) {
    state = { ...state, ...patch };
    applyState();
    const shared = await saveSharedState();
    if (label) say("bot", `${label} ${shared ? "Saved locally." : "Saved locally only."}`);
  }

  window.c3cockEditor = {
    getState: () => ({ ...state }),
    setState: (patch, label) => setSharedPatch(patch, label),
    setTime: (time) => setSharedPatch({ time }, `Switched to ${time} cycle.`),
  };

  toggle.addEventListener("click", () => {
    const closed = panel.classList.toggle("is-closed");
    toggle.setAttribute("aria-expanded", String(!closed));
  });

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    applyPrompt(input.value);
    input.value = "";
  });

  document.querySelectorAll("[data-prompt]").forEach((button) => {
    button.addEventListener("click", () => applyPrompt(button.dataset.prompt || ""));
  });

  reset?.addEventListener("click", async () => {
    state = { ...defaults };
    await persistAndReport(["reset the page to defaults"]);
  });

  async function pollSharedState() {
    if (saving) return;
  }

  async function boot() {
    try {
      state = await loadSharedState();
      lastSeenUpdatedAt = state.updatedAt || "";
      saveLocalState(state);
      applyState();
      say("bot", "Static editor online. Changes persist locally in this browser.");
    } catch {
      state = loadLocalState();
      applyState();
      say("bot", "Shared editor API is offline; using local edits until it returns.");
      warnedOffline = true;
    }

    setInterval(pollSharedState, 5000);
  }

  boot();
})();
