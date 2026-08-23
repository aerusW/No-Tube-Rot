/*
 * settings.js — the schema, and the three things that have to agree with it.
 *
 * A setting is only real if four places know about it: the schema, the menu
 * that draws it, the stylesheets or rulesets that act on it, and the script
 * that wires the two together. Nothing enforces that at runtime — a switch
 * wired to nothing looks exactly like a switch that works until you use it —
 * so it is enforced here instead.
 *
 * The other half of this file is the 2.0 default position: every switch ships
 * off. That is one assertion, and it is the most important one in the suite.
 *
 * Run:  node --test tests/js        (or: python tests/run.py)
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const OPTIONS_HTML = read('options.html');
const OPTIONS_JS = read('options.js');
const CALM_CSS = read('calm.css');
const MANIFEST = JSON.parse(read('manifest.json'));

/** settings.js, evaluated. It touches no API until something calls it. */
function schema() {
  const sandbox = { chrome: { storage: { local: {} } } };
  sandbox.globalThis = sandbox;
  vm.runInNewContext(read('settings.js'), sandbox);
  return sandbox.NTR;
}

const NTR = schema();

/** Every `id="..."` on an input in the menu. */
function controlIds() {
  return [...OPTIONS_HTML.matchAll(/<input\b[^>]*\bid="([^"]+)"/g)].map((m) => m[1]);
}

function accentValues() {
  return [...OPTIONS_HTML.matchAll(/name="accent"\s+value="([^"]+)"/g)].map((m) => m[1]);
}

/* ---- The default position ---------------------------------------------- */

test('every switch is on by default', () => {
  // The default position, in one assertion: a fresh install gives the full
  // effect with nothing to configure. A default of false here is a piece of
  // the extension that silently does nothing for anyone who never opens the
  // menu.
  for (const [key, value] of Object.entries(NTR.DEFAULTS)) {
    if (key === 'accent') continue;
    assert.equal(value, true, `${key} defaults to off`);
  }
});

test('the only setting that is not a switch is the accent', () => {
  const others = Object.entries(NTR.DEFAULTS)
    .filter(([, value]) => typeof value !== 'boolean')
    .map(([key]) => key);
  assert.deepEqual(others, ['accent']);
});

test('the default accent is one the extension actually ships', () => {
  assert.ok(NTR.ACCENTS.includes(NTR.DEFAULTS.accent));
});

test('the accent is a choice, and recolouring is the switch', () => {
  // `accent` has to hold a real value at all times so the palette resolves,
  // which means it cannot itself be the switch. recolourAccent is, and it is
  // a switch like any other.
  assert.equal(typeof NTR.DEFAULTS.recolourAccent, 'boolean');
  assert.equal(typeof NTR.DEFAULTS.accent, 'string');
  assert.ok(!(NTR.DEFAULTS.accent in NTR.ATTRIBUTES),
    'the accent names a palette; it does not gate anything');
});

/* ---- The schema and the menu agree ------------------------------------- */

test('every setting has a control in the menu', () => {
  // With everything off by default, a setting with no control is a feature
  // nobody can ever reach.
  const ids = new Set(controlIds());
  for (const key of Object.keys(NTR.DEFAULTS)) {
    if (key === 'accent') continue;
    assert.ok(ids.has(key), `${key} has no control in options.html`);
  }
});

test('every control in the menu is a real setting', () => {
  for (const id of controlIds()) {
    assert.ok(id in NTR.DEFAULTS, `options.html has a control for unknown "${id}"`);
  }
});

test('the accent is offered exactly as the schema lists it', () => {
  // Spread: ACCENTS is built inside the vm, so it is not the same Array as
  // this realm's, and a strict deep compare would fail on that alone.
  assert.deepEqual(accentValues(), [...NTR.ACCENTS]);
});

test('every fine-tune names a parent that exists', () => {
  const requires = [...OPTIONS_HTML.matchAll(/data-requires="([^"]+)"/g)].map((m) => m[1]);
  assert.ok(requires.length, 'no fine-tunes found; the selector must have changed');
  for (const key of requires) {
    assert.ok(key in NTR.DEFAULTS, `data-requires="${key}" is not a setting`);
  }
});

test('the menu binds by id rather than naming settings one by one', () => {
  // If options.js started listing keys, this file would stop being able to
  // prove the two agree.
  for (const key of Object.keys(NTR.DEFAULTS)) {
    if (key === 'accent') continue;
    assert.ok(!OPTIONS_JS.includes(`'${key}'`),
      `options.js names ${key} directly; bind by id instead`);
  }
});

/* ---- The schema and the browser agree ---------------------------------- */

test('every redirect maps to a ruleset the manifest registers', () => {
  const registered = MANIFEST.declarative_net_request.rule_resources.map((r) => r.id);
  assert.deepEqual(Object.values(NTR.RULESETS).sort(), [...registered].sort());
});

test('every ruleset is reachable from a setting', () => {
  for (const key of Object.keys(NTR.RULESETS)) {
    assert.ok(key in NTR.DEFAULTS, `${key} switches a ruleset but is not a setting`);
  }
});

test('every gate attribute belongs to a setting', () => {
  for (const key of Object.keys(NTR.ATTRIBUTES)) {
    assert.ok(key in NTR.DEFAULTS, `${key} has a CSS gate but is not a setting`);
  }
});

test('no setting both switches a ruleset and gates CSS', () => {
  // The two mechanisms are exclusive; a setting doing both would be applied
  // twice and switched off once.
  for (const key of Object.keys(NTR.RULESETS)) {
    assert.ok(!(key in NTR.ATTRIBUTES), `${key} is wired up twice`);
  }
});

test('every accent has a palette in both themes', () => {
  for (const name of NTR.ACCENTS) {
    for (const prefix of ['html[dark]', 'html:not([dark])']) {
      assert.ok(CALM_CSS.includes(`${prefix}[data-ntr-accent="${name}"]`),
        `${name} has no ${prefix} palette`);
    }
  }
});

/* ---- The docs describe the schema that exists -------------------------- */

test('the README counts the switches correctly', () => {
  // "ask you to make N decisions" is the sentence that carries the whole
  // defaults-on argument, and it is exactly the kind of number that rots
  // silently as switches are added.
  const switches = Object.values(NTR.DEFAULTS)
    .filter((value) => typeof value === 'boolean').length;
  const claimed = read('README.md').match(/make (\d+)\s*\n?decisions/);
  assert.ok(claimed, 'the README no longer states a switch count');
  assert.equal(Number(claimed[1]), switches);
});

test('the README names every accent on offer', () => {
  const readme = read('README.md');
  for (const name of NTR.ACCENTS) {
    assert.ok(readme.includes(`**${name}**`), `the README does not offer ${name}`);
  }
});

/* ---- Storage this version did not write -------------------------------- */

test('missing keys fall back to their defaults', () => {
  assert.deepEqual(NTR.normalise({}), NTR.DEFAULTS);
  assert.deepEqual(NTR.normalise(undefined), NTR.DEFAULTS);
});

test('a value of the wrong type falls back to the default', () => {
  // Storage is writable by hand, and by versions that have not shipped yet.
  for (const junk of ['yes', 1, null, {}]) {
    assert.equal(NTR.normalise({ redirectHome: junk }).redirectHome,
      NTR.DEFAULTS.redirectHome);
  }
});

test('a stored false is honoured', () => {
  // The one that matters now the defaults are on: a switch someone turned
  // off must survive being read back.
  assert.equal(NTR.normalise({ redirectHome: false }).redirectHome, false);
  assert.equal(NTR.normalise({ hideUpNext: false }).hideUpNext, false);
});

test('an unknown accent falls back rather than leaving no palette', () => {
  assert.equal(NTR.normalise({ accent: 'neon' }).accent, NTR.DEFAULTS.accent);
});

test('a key this version does not know is dropped', () => {
  const out = NTR.normalise({ hideEverything: true });
  assert.ok(!('hideEverything' in out));
});

test('a stored true is honoured', () => {
  assert.equal(NTR.normalise({ redirectHome: true }).redirectHome, true);
});
