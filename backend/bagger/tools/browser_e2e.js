#!/usr/bin/env node
const { chromium } = require('/tmp/opencode/node_modules/playwright');

const BASE = 'https://bagger.gulasch.site';

function state(overrides = {}) {
  return {
    schemaVersion: 2,
    player: { name: 'E2E', address: 'du', style: 'earnest' },
    day: 4,
    periodIndex: 1,
    currentRoute: 'aurora',
    lockedRoute: null,
    relationships: {
      aurora: { bond: 10, trust: 2, warmth: 2, depth: 1, courage: 0, mood: 'listening', memories: [], dates: 0, neglect: 0 },
      brummbert: { bond: 0, trust: 0, warmth: 0, depth: 0, courage: 0, mood: 'wach und zugewandt', memories: [], dates: 0, neglect: 0 },
      mira: { bond: 0, trust: 0, warmth: 0, depth: 0, courage: 0, mood: 'wach und zugewandt', memories: [], dates: 0, neglect: 0 },
    },
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
    routePressure: {
      aurora: { toward_romance: 0, toward_friendship: 0, needs_repair: 0, opens_secret: 0, toward_crisis: 0, toward_lockin: 0 },
      brummbert: { toward_romance: 0, toward_friendship: 0, needs_repair: 0, opens_secret: 0, toward_crisis: 0, toward_lockin: 0 },
      mira: { toward_romance: 0, toward_friendship: 0, needs_repair: 0, opens_secret: 0, toward_crisis: 0, toward_lockin: 0 },
    },
    commitmentScore: { aurora: 0, brummbert: 0, mira: 0 },
    promises: [],
    endingState: null,
    settings: { textSpeed: 80, autoSpeed: 3000, skipMode: 'read', nvlMode: 'adv', showFreeText: true },
    debugMeta: { lastTraceId: null },
    ...overrides,
  };
}

async function main() {
  const gameData = await fetch(`${BASE}/api/game-data`).then((r) => r.json());
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('console', (msg) => {
    if (msg.type() === 'error') throw new Error(`browser console error: ${msg.text()}`);
  });

  let currentState = state();
  await page.route('**/api/game-data', (route) => route.fulfill({ json: gameData }));
  await page.route('**/api/new-game', (route) => {
    currentState = state();
    route.fulfill({ json: { ok: true, state: currentState } });
  });
  await page.route('**/api/interact', async (route) => {
    const body = route.request().postDataJSON();
    const intent = body.intent || {};
    currentState = body.state || currentState;
    if (intent.action === 'schedule') {
      currentState = { ...currentState, periodIndex: currentState.periodIndex + 1, currency: currentState.currency + 8, playerStats: { ...currentState.playerStats, fatigue: 12, focus: 1 } };
    } else if (intent.action === 'invite_date') {
      currentState = { ...currentState, periodIndex: currentState.periodIndex + 1, pendingDate: { route: intent.route, location: intent.location, itemId: intent.gift || '', day: 5, periodIndex: 1 } };
    } else if (intent.action === 'start_date') {
      currentState.relationships.aurora.dates += 1;
      currentState.dateHistory.push({ route: 'aurora', location: intent.location, gift: intent.gift || '', fit: 'good' });
    } else {
      currentState = { ...currentState, periodIndex: Math.min(3, currentState.periodIndex + 1) };
    }
    route.fulfill({
      json: {
        state: currentState,
        scene: { id: 'e2e_scene', route: 'aurora', category: 'daily', chapter: 'E2E', premise: 'Testszene', location: 'garage', choiceSet: 'daily' },
        reply: 'E2E Testszene.',
        emotionalRead: 'ruhig',
        deltas: { bondDelta: 0, trustDelta: 0, warmthDelta: 0, depthDelta: 0, courageDelta: 0 },
        routePressure: currentState.routePressure.aurora,
        memory: '',
        visual: 'listening',
        ending: null,
        locationFit: 'neutral',
        commitmentScore: currentState.commitmentScore,
        activePromises: [],
        traceId: 'e2e',
      },
    });
  });

  await page.goto(BASE, { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Neues Spiel' }).click();
  await page.getByRole('button', { name: 'Route beginnen' }).click();
  await page.waitForSelector('#screen-adv:not(.hidden)');

  await page.locator('.qm-btn[data-action="schedule"]').first().click();
  await page.waitForSelector('#screen-schedule:not(.hidden)');
  await page.getByRole('button', { name: /Schicht arbeiten/ }).click();
  await page.waitForSelector('#screen-schedule.hidden');

  await page.locator('.qm-btn[data-action="date"]').first().click();
  await page.waitForSelector('#screen-date:not(.hidden)');
  await page.getByRole('button', { name: 'Für später verabreden' }).click();
  await page.waitForSelector('#screen-date.hidden');

  await page.locator('.qm-btn[data-action="date"]').first().click();
  await page.waitForSelector('#screen-date:not(.hidden)');
  await page.getByRole('button', { name: 'Rendezvous beginnen' }).click();
  await page.waitForSelector('#screen-date.hidden');

  await page.locator('.qm-btn[data-action="settings"]').first().click();
  await page.waitForSelector('#screen-settings:not(.hidden)');
  await page.locator('#set-freetext').uncheck();
  await page.waitForSelector('#free-text-area.hidden');

  await browser.close();
  console.log('ok browser_e2e');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
