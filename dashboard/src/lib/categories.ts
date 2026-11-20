import type { ConditionCategory, LinkageStatus, PayoutStatus, PollutionCategory, ReportStatus } from '@/types/api';

/** Map and chart colours per pollution category: distinct in hue and lightness
 * so they stay apart for colour-blind viewers; labels always accompany them. */
export const CATEGORY_COLOURS: Record<PollutionCategory, string> = {
  OPEN_BURNING: '#C2410C',
  ILLEGAL_DUMPING: '#7A5C12',
  BLOCKED_DRAINAGE: '#1D5F8A',
  MEDICAL_WASTE: '#9D2C6B',
  OTHER: '#5B6B66',
};

export const CONDITION_COLOURS: Record<ConditionCategory, string> = {
  RESPIRATORY: '#0F6E64',
  SKIN: '#9D2C6B',
  DIARRHOEAL: '#1D5F8A',
  MALARIA: '#7A5C12',
  INJURY: '#C2410C',
  INFECTION: '#6B3FA0',
  OTHER: '#5B6B66',
};

type Tone = 'ok' | 'danger' | 'wait' | 'flag' | 'signal' | 'muted';

export const STATUS_TONE: Record<ReportStatus | LinkageStatus | PayoutStatus, Tone> = {
  PENDING: 'wait',
  VERIFIED: 'ok',
  REJECTED: 'danger',
  FLAGGED: 'flag',
  SIGNAL: 'signal',
  NO_SIGNAL: 'muted',
  INSUFFICIENT_DATA: 'muted',
  SUCCESS: 'ok',
  FAILED: 'danger',
};

export const TONE_CLASSES: Record<Tone, string> = {
  ok: 'bg-ok-soft text-ok',
  danger: 'bg-danger-soft text-danger',
  wait: 'bg-wait-soft text-wait',
  flag: 'bg-flag-soft text-flag',
  signal: 'bg-signal-soft text-signal',
  muted: 'bg-mist text-muted',
};
