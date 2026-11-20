import { describe, expect, it } from 'vitest';

import { formatCount, formatP } from '@/lib/format';

describe('formatP', () => {
  it('shows tiny p-values as < 0.001', () => {
    expect(formatP(0.00001)).toBe('< 0.001');
    expect(formatP(0.0423)).toBe('0.042');
    expect(formatP(null)).toBe('');
  });
});

describe('formatCount', () => {
  it('hides suppressed clinic counts behind the threshold (D11)', () => {
    expect(formatCount(null, true, 5, 'en')).toBe('<5');
    expect(formatCount(12, false, 5, 'en')).toBe('12');
    expect(formatCount(7.5, false, 5, 'en')).toBe('7.5');
  });
});
