import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { PayoutsPage } from '@/features/payouts/PayoutsPage';

import { fakeApi, renderWithProviders, signInAs } from './helpers';

const payout = (over: object) => ({
  id: 'p1', report_id: 'r1', report_category: 'OPEN_BURNING', reporter_name: 'Amina', phone_masked: '+2547•••••123',
  amount: '50.00', currency: 'KES', provider: 'MOCK', is_test_payment: true, status: 'SUCCESS',
  transaction_ref: 'MOCK-TXN-1', provider_request_id: null, failure_reason: null, attempts: 1,
  created_at: '2026-11-01T10:00:00Z', last_attempt_at: '2026-11-01T10:00:00Z', paid_at: '2026-11-01T10:00:00Z', ...over,
});

describe('payouts', () => {
  it('badges test payments and offers retry only for failed payouts', async () => {
    signInAs(['ADMINISTRATOR']);
    fakeApi({
      'GET /payouts': {
        items: [payout({}), payout({ id: 'p2', status: 'FAILED', failure_reason: 'Number not registered', transaction_ref: null })],
        total: 2, limit: 25, offset: 0,
      },
    });
    renderWithProviders(<PayoutsPage />);
    expect(await screen.findByText('MOCK-TXN-1')).toBeInTheDocument();
    expect(screen.getAllByText('Test')).not.toHaveLength(0);
    expect(screen.getByText('Number not registered')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Retry' })).toHaveLength(1);
  });
});
