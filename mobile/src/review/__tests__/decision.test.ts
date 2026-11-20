import { ApiError, NetworkError } from '@/api/client';
import { buildQuery } from '@/api/verification';

import { classifyDecisionError, cleanReason, isValidReason, QUICK_REASONS } from '../decision';

test('a reason needs at least 3 real characters', () => {
  expect(isValidReason('')).toBe(false);
  expect(isValidReason('   ab  ')).toBe(false);
  expect(isValidReason('Not pollution')).toBe(true);
  expect(isValidReason('x'.repeat(501))).toBe(false);
});

test('reasons are tidied before sending', () => {
  expect(cleanReason('  Photo   is\nunclear ')).toBe('Photo is unclear');
});

test('offline decisions are reported as not saved, never queued', () => {
  expect(classifyDecisionError(new NetworkError())).toBe('offline');
  expect(classifyDecisionError(new ApiError(409, 'already decided'))).toBe('conflict');
  expect(classifyDecisionError(new ApiError(403, 'own report'))).toBe('forbidden');
  expect(classifyDecisionError(new ApiError(500, 'x'))).toBe('other');
});

test('there are quick reasons for rejecting and flagging', () => {
  expect(QUICK_REASONS.reject.length).toBeGreaterThan(0);
  expect(QUICK_REASONS.flag).toContain('review.reasons.duplicate');
});

test('the default zone filter sends no zone parameter', () => {
  expect(buildQuery({ zone: undefined, limit: 20, offset: 0 })).toBe('?limit=20&offset=0');
  expect(buildQuery({ zone: 'NBI-DANDORA', limit: 20 })).toBe('?zone=NBI-DANDORA&limit=20');
});
