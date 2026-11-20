import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { App } from '@/App';
import type { Overview } from '@/types/api';

import { fakeApi, renderWithProviders, signInAs } from './helpers';

const overview: Overview = {
  total: 20,
  by_status: { PENDING: 3, VERIFIED: 14, REJECTED: 2, FLAGGED: 1 },
  verified_by_category: { OPEN_BURNING: 8, ILLEGAL_DUMPING: 4, BLOCKED_DRAINAGE: 2, MEDICAL_WASTE: 0, OTHER: 0 },
  verified_last_7_days: 5,
  top_zones: [{ zone_code: 'DANDORA', zone_name: 'Dandora', verified: 9 }],
  linkages_by_status: { SIGNAL: 2, NO_SIGNAL: 6, INSUFFICIENT_DATA: 2 },
  payouts: null,
};

const trends = {
  by_status: { SIGNAL: 1, NO_SIGNAL: 0, INSUFFICIENT_DATA: 0 },
  by_condition: {},
  notice: 'association',
  clusters: [
    {
      facility_id: 'f1', facility_code: 'DND-01', facility_name: 'Dandora Health Centre', area_code: 'EMB',
      latitude: -1.25, longitude: 36.9, condition_category: 'RESPIRATORY', signal_reports: 3,
      pollution_categories: ['OPEN_BURNING'], max_rate_ratio: 1.84, min_p_value: 0.0002, latest_report_at: '2026-10-01T10:00:00Z',
    },
  ],
};

const api = () =>
  fakeApi({
    'GET /dashboard/overview': overview,
    'GET /health-linkage/trends': trends,
    'GET /zones': [],
  });

describe('overview and role-based navigation', () => {
  it('agency staff see the overview with verified figures and signals, but no administration pages', async () => {
    api();
    signInAs(['AGENCY_STAFF']);
    renderWithProviders(<App />);

    expect(await screen.findByTestId('verified-count')).toHaveTextContent('14');
    expect(await screen.findByText('Dandora Health Centre')).toBeInTheDocument();
    expect(screen.getByText(/not proof that pollution caused illness/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Users' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Payouts' })).not.toBeInTheDocument();
  });

  it('administrators also get the administration section', async () => {
    api();
    signInAs(['ADMINISTRATOR']);
    renderWithProviders(<App />);
    expect(await screen.findByRole('link', { name: 'Users' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Clinic data' })).toBeInTheDocument();
  });

  it('agency staff who open an administration address are sent back to the overview', async () => {
    api();
    signInAs(['AGENCY_STAFF']);
    renderWithProviders(<App />, { route: '/users' });
    expect(await screen.findByTestId('verified-count')).toBeInTheDocument();
  });
});
