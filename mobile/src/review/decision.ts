/** Rules and helpers for the verifier's decision form (mirror the API rules). */
import { ApiError, NetworkError } from '@/api/client';

export const MIN_REASON_LENGTH = 3;
export const MAX_REASON_LENGTH = 500;

export type ReasonAction = 'reject' | 'flag';

/** Translation keys for one-tap reasons. */
export const QUICK_REASONS: Record<ReasonAction, string[]> = {
  reject: [
    'review.reasons.unclear',
    'review.reasons.notPollution',
    'review.reasons.wrongLocation',
    'review.reasons.wrongCategory',
  ],
  flag: ['review.reasons.duplicate', 'review.reasons.secondOpinion'],
};

export function cleanReason(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

export function isValidReason(text: string): boolean {
  const cleaned = cleanReason(text);
  return cleaned.length >= MIN_REASON_LENGTH && cleaned.length <= MAX_REASON_LENGTH;
}

export type DecisionFailure = 'offline' | 'conflict' | 'forbidden' | 'other';

/** What a failed decision means for the verifier. Offline decisions are NOT queued. */
export function classifyDecisionError(error: unknown): DecisionFailure {
  if (error instanceof NetworkError) return 'offline';
  if (error instanceof ApiError && error.status === 409) return 'conflict';
  if (error instanceof ApiError && error.status === 403) return 'forbidden';
  return 'other';
}
