/**
 * One visual identity for the mobile app (the dashboard reuses these colours).
 * Teal = environment and health; amber = caution. All text/background pairs
 * meet WCAG AA contrast (4.5:1) for normal text.
 */
export const colors = {
  primary: '#0F6E64',
  primaryDark: '#0A524A',
  primarySoft: '#E3F1EE',
  background: '#F6F8F7',
  surface: '#FFFFFF',
  text: '#1C2A28',
  textMuted: '#4E5D5A',
  border: '#D5DEDB',
  danger: '#B42318',
  dangerSoft: '#FDECEA',
  warning: '#8A5300',
  warningSoft: '#FFF4DE',
  success: '#1E7A3C',
  successSoft: '#E5F4EA',
  flagged: '#6B3FA0',
  flaggedSoft: '#F1EAFA',
  queued: '#33547A',
  queuedSoft: '#E7EEF7',
};

export const spacing = { xs: 4, sm: 8, md: 16, lg: 24, xl: 32 };

export const radius = { sm: 8, md: 12, lg: 16 };

export const font = {
  small: 14,
  body: 16,
  large: 18,
  title: 22,
  hero: 28,
};

/** Minimum touch target recommended for accessibility. */
export const TOUCH_TARGET = 48;
