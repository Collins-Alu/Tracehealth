import { describe, expect, it } from 'vitest';

import en from '@/i18n/en.json';
import sw from '@/i18n/sw.json';

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    v && typeof v === 'object' ? keys(v, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

describe('translations', () => {
  it('Kiswahili has every English key, and no extra ones', () => {
    expect(keys(sw).sort()).toEqual(keys(en).sort());
  });

  it('no translation is left empty', () => {
    const values = (o: object): string[] => Object.values(o).flatMap((v) => (typeof v === 'object' ? values(v) : [v]));
    expect(values(en).filter((v) => !v.trim())).toEqual([]);
    expect(values(sw).filter((v) => !v.trim())).toEqual([]);
  });
});
