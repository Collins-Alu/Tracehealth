/** NFR 3: every English string has a Swahili translation, and none are blank. */
import en from '../en.json';
import sw from '../sw.json';

function flatten(obj: object, prefix = ''): Record<string, string> {
  return Object.entries(obj).reduce<Record<string, string>>((acc, [k, v]) => {
    const key = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === 'object') Object.assign(acc, flatten(v, key));
    else acc[key] = String(v);
    return acc;
  }, {});
}

const enKeys = flatten(en);
const swKeys = flatten(sw);

test('English and Swahili have exactly the same keys', () => {
  expect(Object.keys(swKeys).sort()).toEqual(Object.keys(enKeys).sort());
});

test('no translation is empty', () => {
  for (const [key, value] of Object.entries({ ...enKeys, ...swKeys })) {
    expect(`${key}=${value.trim()}`).not.toBe(`${key}=`);
  }
});

test('placeholders like {{count}} match between languages', () => {
  const vars = (s: string) => (s.match(/{{\s*\w+\s*}}/g) ?? []).sort();
  for (const key of Object.keys(enKeys)) {
    expect([key, vars(swKeys[key])]).toEqual([key, vars(enKeys[key])]);
  }
});

test('every report category and status has a label', () => {
  for (const c of ['OPEN_BURNING', 'ILLEGAL_DUMPING', 'BLOCKED_DRAINAGE', 'MEDICAL_WASTE', 'OTHER']) {
    expect(enKeys[`categories.${c}`]).toBeTruthy();
  }
  for (const s of ['PENDING', 'VERIFIED', 'REJECTED', 'FLAGGED', 'QUEUED', 'SYNCING', 'NEEDS_ATTENTION']) {
    expect(enKeys[`status.${s}`]).toBeTruthy();
  }
});

test('the safety reminder warns against approaching hazards in both languages', () => {
  expect(enKeys['safety.text']).toMatch(/safe distance/i);
  expect(enKeys['safety.text']).toMatch(/never/i);
  expect(swKeys['safety.text']).toMatch(/umbali salama/i);
});
