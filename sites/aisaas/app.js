const form = document.querySelector("#lead-form");
const results = document.querySelector("#results");
const copyButton = document.querySelector("#copy-button");
const chatForm = document.querySelector("#chat-form");
const chatInput = document.querySelector("#chat-input");
const chatLog = document.querySelector("#chat-log");
const chatSuggestions = document.querySelectorAll(".chat-suggestion");
const fullscreenNotifications = document.querySelector("#fullscreen-notifications");

let topEmail = "";
let currentLeadContext = "";

const staticAiResponses = {
  chat: [
    {
      match: ["email", "outreach", "draft"],
      reply: "Lead with the strongest buying signal, name the operational pain, and ask for one short next step. Keep it under six sentences.",
    },
    {
      match: ["rank", "prioritize", "next"],
      reply: "Prioritize accounts with hiring, support load, or recent growth signals. Those are the easiest places to prove urgency.",
    },
    {
      match: ["notification", "alert"],
      reply: "Pipeline alert\nHot lead pattern\nNorthstar Ledger is lighting up multiple buying signals at once.",
    },
  ],
  fallback: "Move fast on the highest-fit account: use the visible buying signal, keep the ask small, and follow up with one concrete next step.",
  notifications: [
    ["Pipeline alert", "Hot lead pattern", "Northstar Ledger is lighting up multiple buying signals at once."],
    ["ScoutBot says", "Rank again", "The account list has more signal hiding in plain sight."],
    ["Revenue alert", "Stop scrolling", "There is a 94-fit account waiting for a better first touch."],
  ],
};

function wordsFrom(value) {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter((word) => word.length > 2);
}

function parseCompanies(value) {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, ...details] = line.split("|").map((part) => part.trim());
      return { name, details: details.join(" ") || line };
    });
}

function scoreCompany(company, industries, signals) {
  const text = `${company.name} ${company.details}`.toLowerCase();
  const industryHits = industries.filter((word) => text.includes(word));
  const signalHits = signals.filter((word) => text.includes(word));
  const employeeMatch = text.match(/(\d+)\s*employees?/);
  const employees = employeeMatch ? Number(employeeMatch[1]) : 0;
  const sizeScore = employees >= 50 && employees <= 500 ? 18 : employees > 500 ? 10 : employees >= 20 ? 8 : 0;
  const growthScore = /(hiring|raised|growth|expanding|thousands|many|series)/.test(text) ? 18 : 0;
  const score = Math.min(98, 22 + industryHits.length * 14 + signalHits.length * 10 + sizeScore + growthScore);

  return {
    ...company,
    score,
    tags: [...new Set([...industryHits, ...signalHits])].slice(0, 6),
    reason: buildReason(company, score, industryHits, signalHits, employees, growthScore),
  };
}

function buildReason(company, score, industryHits, signalHits, employees, growthScore) {
  const reasons = [];

  if (industryHits.length) reasons.push(`matches your target market: ${industryHits.join(", ")}`);
  if (signalHits.length) reasons.push(`shows buying signals: ${signalHits.join(", ")}`);
  if (employees) reasons.push(`has enough team size to feel the pain (${employees} employees)`);
  if (growthScore) reasons.push("looks like it is growing or adding workload");
  if (!reasons.length) reasons.push("has limited fit based on the details provided");

  return `${company.name} scored ${score}/100 because it ${reasons.join(" and ")}.`;
}

function makeEmail(company, offer) {
  return `Subject: quick idea for ${company.name}\n\nHi there,\n\nNoticed ${company.name} looks like a strong fit for ${offer}. If your team is dealing with more customer conversations, we can help cut the manual work and keep replies fast.\n\nWorth a 15-minute chat this week?`;
}

function escapeHtml(value) {
  return value.replace(/[&<>"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
  })[character]);
}

function render() {
  const data = new FormData(form);
  const offer = data.get("offer").trim();
  const industries = wordsFrom(data.get("industries"));
  const signals = wordsFrom(data.get("signals"));
  const ranked = parseCompanies(data.get("companies"))
    .map((company) => scoreCompany(company, industries, signals))
    .sort((a, b) => b.score - a.score);

  topEmail = ranked[0] ? makeEmail(ranked[0], offer) : "";
  currentLeadContext = `Offer: ${offer}\nIndustries: ${data.get("industries")}\nSignals: ${data.get("signals")}\nTop leads: ${ranked.map((company) => `${company.name} ${company.score}/100 - ${company.reason}`).join(" | ")}`;

  results.innerHTML = ranked
    .map((company, index) => {
      const email = index === 0 ? makeEmail(company, offer) : "";
      return `
        <article class="lead-card">
          <div class="score" style="--score: ${company.score}%"><span>${company.score}</span></div>
          <div>
            <h3>${escapeHtml(company.name)}</h3>
            <p class="reason">${escapeHtml(company.reason)}</p>
            <div class="tags">${company.tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("") || '<span class="tag">needs more data</span>'}</div>
            ${email ? `<p class="email">${escapeHtml(email).replaceAll("\n", "<br />")}</p>` : ""}
          </div>
        </article>
      `;
    })
    .join("");
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  render();
});

copyButton.addEventListener("click", async () => {
  if (!topEmail) return;
  await navigator.clipboard.writeText(topEmail);
  copyButton.textContent = "Copied";
  setTimeout(() => {
    copyButton.textContent = "Copy email";
  }, 1400);
});

function addMessage(text, type) {
  const message = document.createElement("div");
  message.className = `message ${type}`;
  message.textContent = text;
  chatLog.append(message);
  chatLog.scrollTop = chatLog.scrollHeight;
  return message;
}

async function sendChatMessage(message) {
  if (!message) return;

  chatInput.value = "";
  addMessage(message, "user");
  const pending = addMessage("Thinking...", "bot");

  pending.textContent = staticChatReply(message);
}

function staticChatReply(message) {
  const text = `${message} ${currentLeadContext}`.toLowerCase();
  const hit = staticAiResponses.chat.find((item) => item.match.some((word) => text.includes(word)));
  return hit ? hit.reply : staticAiResponses.fallback;
}

chatForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendChatMessage(chatInput.value.trim());
});

chatSuggestions.forEach((button) => {
  button.addEventListener("click", async () => {
    await sendChatMessage(button.dataset.prompt);
  });
});

render();
startDeviceLeveling();
startPersistentNagging();
startFullscreenNotifications();

function startDeviceLeveling() {
  const supportsOrientation = "DeviceOrientationEvent" in window;

  if (!supportsOrientation) return;

  const level = { x: 0, y: 0, z: 0 };
  const clamp = (value, max) => Math.max(-max, Math.min(max, value));
  let frame = 0;

  const applyLevel = () => {
    frame = 0;
    document.body.dataset.leveling = "active";
    document.documentElement.style.setProperty("--level-x", `${clamp(level.x, 14).toFixed(2)}deg`);
    document.documentElement.style.setProperty("--level-y", `${clamp(level.y, 14).toFixed(2)}deg`);
    document.documentElement.style.setProperty("--level-z", `${clamp(level.z, 10).toFixed(2)}deg`);
  };

  const setLevel = (changes) => {
    Object.assign(level, changes);
    if (!frame) frame = requestAnimationFrame(applyLevel);
  };

  const screenAngle = () => {
    const angle = window.screen?.orientation?.angle ?? window.orientation ?? 0;
    return ((Number(angle) % 360) + 360) % 360;
  };

  const viewportTilt = (beta, gamma) => {
    switch (screenAngle()) {
      case 90:
        return { roll: beta, pitch: -gamma };
      case 180:
        return { roll: -gamma, pitch: -beta };
      case 270:
        return { roll: -beta, pitch: gamma };
      default:
        return { roll: gamma, pitch: beta };
    }
  };

  const handleOrientation = ({ beta, gamma }) => {
    if (typeof beta !== "number" || typeof gamma !== "number") return;
    const { roll, pitch } = viewportTilt(beta, gamma);

    setLevel({
      x: clamp(pitch / 12, 4),
      y: clamp(-roll / 12, 4),
      z: clamp(-roll / 4, 12),
    });
  };

  const attachListeners = () => {
    window.addEventListener("deviceorientation", handleOrientation);
  };

  const requestOrientationPermission = window.DeviceOrientationEvent && DeviceOrientationEvent.requestPermission;

  if (!requestOrientationPermission) {
    attachListeners();
    return;
  }

  const requestPermissions = async () => {
    document.removeEventListener("pointerdown", requestPermissions);

    try {
      const orientationGranted = (await DeviceOrientationEvent.requestPermission()) === "granted";

      if (orientationGranted) attachListeners();
    } catch {
      attachListeners();
    }
  };

  document.addEventListener("pointerdown", requestPermissions, { once: true });
}

function startPersistentNagging() {
  const nags = [
    "Northstar Ledger is glowing on the dashboard. Move fast.",
    "The safe email is too sleepy. Give it sharper edges.",
    "Your targeting is whispering. Let it speak up.",
    "Pipeline gremlin says: rank the leads again.",
    "Gemini spotted a hot lead pattern. Ask for the next move.",
    "A 94-fit account is sitting right there. Do not waste it.",
  ];
  let index = 0;

  setInterval(() => {
    addMessage(nags[index % nags.length], "bot urgent");
    index += 1;

    while (chatLog.children.length > 8) {
      chatLog.firstElementChild.remove();
    }
  }, 4200);
}

function startFullscreenNotifications() {
  if (!fullscreenNotifications) return;

  const fallbackNotifications = [
    ["Pipeline alert", "Hot lead pattern", "Northstar Ledger is lighting up multiple buying signals at once."],
    ["ScoutBot says", "Rank again", "The account list has more signal hiding in plain sight."],
    ["Gemini signal", "Sharpen the email", "The safest draft may not be the one that books the meeting."],
    ["Signal spike", "Support hiring", "Ticket volume points to real automation pain."],
    ["Revenue alert", "Stop scrolling", "There is a 94-fit account waiting for a better first touch."],
    ["Forecast anomaly", "Buyers detected", "The spreadsheet is pointing at urgent opportunities."],
  ];
  let index = 0;
  const generatedNotifications = [...staticAiResponses.notifications];

  showFullscreenNotification(fallbackNotifications[index]);
  index += 1;

  setInterval(() => {
    const fallback = fallbackNotifications[index % fallbackNotifications.length];
    showFullscreenNotification(generatedNotifications.shift() || fallback);
    index += 1;
  }, 2500);

  setInterval(() => {
    generatedNotifications.push(staticAiResponses.notifications[index % staticAiResponses.notifications.length]);
    while (generatedNotifications.length > 3) generatedNotifications.shift();
  }, 12000);
}

async function requestGeneratedNotification(queue, fallback) {
  queue.push(fallback);
  while (queue.length > 3) queue.shift();
}

function parseGeneratedNotification(reply, fallback) {
  const lines = reply
    .split("\n")
    .map((line) => line.replace(/^[-*\d.\s]+/, "").trim())
    .filter(Boolean)
    .slice(0, 3);

  if (lines.length < 3) return fallback;
  return [lines[0].slice(0, 32), lines[1].slice(0, 42), lines[2].slice(0, 130)];
}

function showFullscreenNotification([label, headline, detail]) {
  const notification = document.createElement("div");
  notification.className = "fullscreen-notification";
  notification.innerHTML = `
    <span>${escapeHtml(label)}</span>
    <strong>${escapeHtml(headline)}</strong>
    <p>${escapeHtml(detail)}</p>
  `;

  fullscreenNotifications.append(notification);
  setTimeout(() => notification.remove(), 2900);
}
