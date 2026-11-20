import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LinkageTable } from '@/features/trends/LinkageTable';
import type { Linkage } from '@/types/api';

const base: Linkage = {
  id: 'l1', status: 'SIGNAL', insufficient_reason: null, condition_category: 'RESPIRATORY', report_id: 'r1',
  report_category: 'OPEN_BURNING', report_captured_at: '2026-10-01T09:00:00Z', report_zone_code: 'DANDORA',
  facility_code: 'DND-01', facility_name: 'Dandora Health Centre', facility_area_code: 'EMB', distance_km: 1.234,
  radius_km: 3, baseline_visits: 400, followup_visits: 380, baseline_days: 56, followup_days: 28,
  rate_ratio: 1.9, p_value: 0.00001, correlation_score: 0.3, detected_at: '2026-10-02T00:00:00Z',
};

describe('LinkageTable', () => {
  it('shows the rate change, p-value and weekly rates for a signal', () => {
    render(<LinkageTable items={[base]} />);
    expect(screen.getByText('Signal')).toBeInTheDocument();
    expect(screen.getByText('×1.90')).toBeInTheDocument();
    expect(screen.getByText('< 0.001')).toBeInTheDocument();
    expect(screen.getByText('50.0/wk')).toBeInTheDocument(); // 400 visits over 56 days
    expect(screen.getByText('95.0/wk')).toBeInTheDocument(); // 380 visits over 28 days
  });

  it('explains why a result has no statistics instead of inventing any', () => {
    render(
      <LinkageTable
        items={[{ ...base, status: 'INSUFFICIENT_DATA', insufficient_reason: 'baseline_coverage', rate_ratio: null, p_value: null }]}
      />,
    );
    expect(screen.getByText('Not enough data')).toBeInTheDocument();
    expect(screen.getByText('Too little clinic data before the report')).toBeInTheDocument();
    expect(screen.queryByText(/×/)).not.toBeInTheDocument();
  });
});
