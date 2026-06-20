#!/usr/bin/env node
const { chromium } = require('/opt/bagger-api/node_modules/playwright');

const baseState = () => ({
  schemaVersion: 2,
  player: { name: 'E2E', address: 'du', style: 'earnest' },
  day: 1,
  periodIndex: 0,
  currentRoute: 'aurora',
  lockedRoute: null,
  relationships: Object.fromEntries(['aurora', 'brummbert', 'mira'].map(route => [route, {
    bond: 0, trust: 0, warmth: 0, depth: 0, courage: 0,
    mood: route === 'aurora' ? 'vorsichtig neugierig' : 'wach und zugewandt',
    memories: [], dates: 0, neglect: 0,
  }])),
  playerStats: { mechanics: 0, charm: 2, patience: 2, courage: 0, focus: 0, fatigue: 0 },
  flags: [],
  inventory: { kiesel: 1 },
  currency: 20,
  backlog: [],
  eventsSeen: [],
  calendarState: { missed: [] },
  dateHistory: [],
  pendingDate: null,
  locationHistory: {},
  giftHistory: [],
  sceneCooldowns: {},
  lastAction: null,
  routePressure: Object.fromEntries(['aurora', 'brummbert', 'mira'].map(route => [route, {
    toward_romance: 0, toward_friendship: 0, needs_repair: 0,
    opens_secret: 0, toward_crisis: 0, toward_lockin: 0,
  }])),
  commitmentScore: { aurora: 0, brummbert: 0, mira: 0 },
  promises: [],
  endingState: null,
  settings: { textSpeed: 80, autoSpeed: 3000, skipMode: 'read', nvlMode: 'adv', showFreeText: true },
  debugMeta: { lastTraceId: null },
});

function advanceTime(state) {
  state.periodIndex += 1;
  if (state.periodIndex >= 4) {
    state.periodIndex = 0;
    state.day += 1;
  }
}

function scene(route = 'aurora', category = 'daily') {
  return {
    id: `${route}_${category}_e2e`,
    route,
    category,
    chapter: 'E2E',
    premise: 'Browser-Testszene auf dem Bauhof.',
    location: 'garage',
    periodAffinity: ['Morgen', 'Nachmittag', 'Abend', 'Nacht'],
    requiredFlags: [],
    blockedByFlags: [],
    statHints: {},
    motifs: ['Kaffeebecher'],
    choiceSet: category,
    nextCandidates: [],
    routePressureEffects: {},
    setsFlags: [],
    translationStyleNotes: {},
  };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  let state = baseState();

  await page.route('**/api/new-game', async route => {
    state = baseState();
    await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ ok: true, state }) });
  });

  await page.route('**/api/interact', async route => {
    const body = route.request().postDataJSON();
    const intent = body.intent || {};
    const action = intent.action || intent.type || 'advance';
    let selectedScene = scene(state.currentRoute, 'daily');
    let reply = 'E2E: Der Motor brummt kurz. Alles reagiert.';

    if (action === 'schedule') {
      state.currency += intent.activity === 'work' ? 8 : 0;
      state.playerStats.fatigue = Math.min(150, state.playerStats.fatigue + 12);
      state.playerStats.focus += 1;
      selectedScene = scene(state.currentRoute, 'daily');
    } else if (action === 'start_date') {
      const routeId = intent.route || state.currentRoute;
      state.currentRoute = routeId;
      state.relationships[routeId].dates += 1;
      state.dateHistory.push({ route: routeId, location: intent.location, gift: intent.gift || '', day: state.day, period: state.periodIndex });
      if (intent.gift && state.inventory[intent.gift]) state.inventory[intent.gift] -= 1;
      selectedScene = scene(routeId, 'date');
      reply = 'E2E: Das Rendezvous findet statt.';
    } else if (action === 'invite_date') {
      const day = state.periodIndex < 1 ? state.day : state.day + 1;
      state.pendingDate = { route: intent.route || state.currentRoute, location: intent.location, itemId: intent.gift || '', day, periodIndex: 1, createdDay: state.day };
      reply = 'Abgemacht. Aurora 7000 merkt sich Nachmittag.';
      advanceTime(state);
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ state, reply, scene: null, ending: null, pendingDate: state.pendingDate }) });
      return;
    } else if (action === 'buy') {
      state.currency -= 14;
      state.inventory.star_map = (state.inventory.star_map || 0) + 1;
      advanceTime(state);
      await route.fulfill({ contentType: 'application/json', body: JSON.stringify({ state, reply: 'Item gekauft.', scene: null, buy: { ok: true } }) });
      return;
    } else {
      selectedScene = scene(state.currentRoute, 'intro');
    }

    advanceTime(state);
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        state,
        scene: selectedScene,
        calendarEvent: null,
        reply,
        emotionalRead: 'e2e',
        deltas: { bondDelta: 0, trustDelta: 0, warmthDelta: 0, depthDelta: 0, courageDelta: 0 },
        routePressure: state.routePressure[state.currentRoute],
        memory: 'E2E Erinnerung',
        visual: 'listening',
        ending: null,
        locationFit: 'neutral',
        commitmentScore: state.commitmentScore,
        activePromises: [],
        traceId: 'e2e',
      }),
    });
  });

  await page.goto('https://bagger.gulasch.site', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Neues Spiel' }).click();
  await page.locator('#player-name').fill('E2E');
  await page.locator('#setup-form button[type="submit"]').click();
  await page.locator('#screen-adv:not(.hidden)').waitFor({ timeout: 10000 });

  await page.locator('.qm-btn[data-action="schedule"]').first().click();
  await page.locator('#screen-schedule:not(.hidden)').waitFor();
  await page.getByText('Schicht arbeiten').click();
  await page.locator('#screen-schedule').waitFor({ state: 'hidden' });

  await page.locator('.qm-btn[data-action="date"]').first().click();
  await page.locator('#screen-date:not(.hidden)').waitFor();
  await page.locator('#date-location').selectOption('garage');
  await page.locator('#date-invite').click();
  await page.locator('#screen-date').waitFor({ state: 'hidden' });

  await page.locator('.qm-btn[data-action="date"]').first().click();
  await page.locator('#screen-date:not(.hidden)').waitFor();
  await page.locator('#date-location').selectOption('garage');
  await page.locator('#date-start').click();
  await page.locator('#screen-date').waitFor({ state: 'hidden' });

  await page.locator('.qm-btn[data-action="status"]').first().click();
  await page.locator('#screen-status:not(.hidden)').waitFor();
  const datesText = await page.locator('#s-dates').textContent();
  if (!datesText || Number(datesText) < 1) throw new Error(`expected dates >= 1, got ${datesText}`);

  await browser.close();
  console.log('ok e2e_browser_test');
}

main().catch(async error => {
  console.error(error);
  process.exit(1);
});
