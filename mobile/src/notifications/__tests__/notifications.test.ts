import { pushSupport } from '../pushSupport';
import { notificationTarget } from '../routing';

describe('notificationTarget', () => {
  test('verifiers go to the review screen for new reports', () => {
    expect(notificationTarget('report.submitted', 'r1', ['VERIFIER'])).toBe('/review/r1');
  });
  test('reporters go to their report for decisions', () => {
    expect(notificationTarget('report.verified', 'r1', ['REPORTER'])).toBe('/report/r1');
    expect(notificationTarget('report.rejected', 'r1', ['REPORTER', 'VERIFIER'])).toBe('/report/r1');
  });
  test('reward messages open the report they are for', () => {
    expect(notificationTarget('payout.sent', 'r1', ['REPORTER'])).toBe('/report/r1');
    expect(notificationTarget('payout.failed', 'r1', ['REPORTER'])).toBe('/report/r1');
    expect(notificationTarget('payout.sent', 'r1', ['VERIFIER'])).toBeNull();
  });
  test('nothing to open without a report or a matching role', () => {
    expect(notificationTarget('report.verified', null, ['REPORTER'])).toBeNull();
    expect(notificationTarget('report.submitted', 'r1', ['REPORTER'])).toBeNull();
  });
});

describe('pushSupport', () => {
  const device = {
    platform: 'android',
    isDevice: true,
    executionEnvironment: 'standalone',
    projectId: 'abc',
  };
  test('a real build on a phone with a project id can receive push', () => {
    expect(pushSupport(device)).toEqual({ supported: true });
  });
  test.each([
    [{ executionEnvironment: 'storeClient' }, 'EXPO_GO'],
    [{ isDevice: false }, 'NOT_A_DEVICE'],
    [{ projectId: undefined }, 'NO_PROJECT_ID'],
    [{ platform: 'web' }, 'WEB'],
  ] as [Partial<typeof device>, string][])('%p -> %s', (override, reason) => {
    expect(pushSupport({ ...device, ...override })).toEqual({ supported: false, reason });
  });
});
