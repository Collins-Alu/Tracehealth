/** Formatting helpers shared by every page. */

export function formatDate(iso: string | null | undefined, lang: string, withTime = false): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(lang === 'sw' ? 'sw-KE' : 'en-KE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    ...(withTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  });
}

export function formatNumber(n: number | null | undefined, lang: string, digits = 0): string {
  if (n === null || n === undefined) return '';
  return n.toLocaleString(lang === 'sw' ? 'sw-KE' : 'en-KE', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Clinic counts below the threshold are hidden (D11) and shown as "<5". */
export function formatCount(n: number | null, suppressed: boolean, threshold: number, lang: string) {
  if (suppressed) return `<${threshold}`;
  return formatNumber(n, lang, n !== null && !Number.isInteger(n) ? 1 : 0);
}

/** p-values: "< 0.001" rather than a long string of zeros. */
export function formatP(p: number | null): string {
  if (p === null) return '';
  if (p < 0.001) return '< 0.001';
  return p.toFixed(3);
}

export function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function daysAgo(n: number): string {
  return isoDate(new Date(Date.now() - n * 86_400_000));
}
