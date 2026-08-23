/*
 * The menu's behaviour.
 *
 * Controls are bound by id: every id in options.html is a key in NTR.DEFAULTS,
 * so nothing here names a setting individually and adding one is an HTML
 * change plus a schema change, never a third edit that is easy to forget.
 *
 * This page is also the only place that switches the declarativeNetRequest
 * rulesets on and off. There is no background worker to do it — the redirect
 * rules are static and registered disabled in the manifest, and enabling a
 * ruleset is a single call an extension page is allowed to make. The state
 * lives in the browser rather than in storage, so the two are reconciled
 * whenever this page opens, and a ruleset can never be left switched on for a
 * setting that has since been switched off.
 */
'use strict';

const { api, DEFAULTS, RULESETS, ACCENTS } = globalThis.NTR;

const BOOLEANS = Object.keys(DEFAULTS).filter((key) => key !== 'accent');

/* ---- declarativeNetRequest ---------------------------------------------- */

async function syncRulesets(settings) {
  const enableRulesetIds = [];
  const disableRulesetIds = [];
  for (const [key, id] of Object.entries(RULESETS)) {
    (settings[key] ? enableRulesetIds : disableRulesetIds).push(id);
  }
  try {
    await api.declarativeNetRequest.updateEnabledRulesets({
      enableRulesetIds, disableRulesetIds,
    });
    return true;
  } catch {
    // Support for static rulesets varies between engines and versions. A
    // switch that flips and silently does nothing is the worst outcome here,
    // so say so instead — the rest of the menu keeps working.
    document.getElementById('redirectNote').hidden = false;
    return false;
  }
}

/* ---- Drawing ------------------------------------------------------------ */

/** Fine-tunes are shown whatever their parent is doing, but not operable. */
function updateDependencies(settings) {
  for (const node of document.querySelectorAll('[data-requires]')) {
    const enabled = settings[node.dataset.requires] === true;
    node.setAttribute('aria-disabled', String(!enabled));
    for (const input of node.querySelectorAll('input')) input.disabled = !enabled;
  }
}

function draw(settings) {
  for (const key of BOOLEANS) {
    const input = document.getElementById(key);
    if (input) input.checked = settings[key];
  }
  for (const radio of document.querySelectorAll('input[name="accent"]')) {
    radio.checked = radio.value === settings.accent;
  }
  updateDependencies(settings);
}

/* ---- Wiring ------------------------------------------------------------- */

async function onChange(patch) {
  await globalThis.NTR.write(patch);
  const settings = await globalThis.NTR.read();
  // Only the redirects touch the rulesets, so only they need the call.
  if (Object.keys(patch).some((key) => key in RULESETS)) await syncRulesets(settings);
  draw(settings);
}

function bind() {
  for (const key of BOOLEANS) {
    const input = document.getElementById(key);
    if (input) input.addEventListener('change', () => onChange({ [key]: input.checked }));
  }
  for (const radio of document.querySelectorAll('input[name="accent"]')) {
    radio.addEventListener('change', () => {
      if (radio.checked && ACCENTS.includes(radio.value)) onChange({ accent: radio.value });
    });
  }
  document.getElementById('reset').addEventListener('click', () => onChange({ ...DEFAULTS }));

  // Keep a popup and an open options tab from showing different answers.
  api.storage.onChanged.addListener(async (_changes, area) => {
    if (area === 'local') draw(await globalThis.NTR.read());
  });
}

async function start() {
  // Firefox draws its own picture-in-picture control and exposes no API for
  // it, so say so rather than offering switches that quietly do nothing.
  if (document.pictureInPictureEnabled !== true) {
    document.getElementById('pipNote').hidden = false;
  }
  const settings = await globalThis.NTR.read();
  draw(settings);
  bind();
  await syncRulesets(settings);
}

start();
