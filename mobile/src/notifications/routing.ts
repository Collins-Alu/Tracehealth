import type { Role } from '@/api/types';

/**
 * Where tapping a notification (in the inbox or a push banner) should go.
 *   New report for verifiers -> the review screen
 *   Decisions for reporters  -> the reporter's report details
 */
export function notificationTarget(
  type: string | undefined,
  reportId: string | null | undefined,
  roles: Role[],
): string | null {
  if (!reportId) return null;
  if (type === 'report.submitted') return roles.includes('VERIFIER') ? `/review/${reportId}` : null;
  if (type && REPORTER_EVENTS.has(type) && roles.includes('REPORTER')) return `/report/${reportId}`;
  return null;
}

const REPORTER_EVENTS = new Set([
  'report.verified',
  'report.rejected',
  'report.flagged',
  'payout.sent',
  'payout.failed',
]);
