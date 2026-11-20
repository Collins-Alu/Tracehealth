import { api } from './index';
import type { DecisionResult, NearbyReport, Report, ReportPage, Zone } from './types';

/**
 * Zone filter values sent to the API:
 *   undefined     my zone plus unassigned reports (the default)
 *   'ALL'         every zone
 *   'UNASSIGNED'  reports outside every zone
 *   a zone code   that zone only
 */
export type ZoneFilter = string | undefined;

function query(params: Record<string, string | number | undefined>) {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== '')
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join('&')}` : '';
}

export const verificationApi = {
  zones: () => api.request<Zone[]>('/zones'),

  pending: (zone: ZoneFilter, limit = 20, offset = 0) =>
    api.request<ReportPage>(`/reports/pending${query({ zone, limit, offset })}`),

  flagged: (zone: ZoneFilter, limit = 20, offset = 0) =>
    api.request<ReportPage>(`/reports/flagged${query({ zone, limit, offset })}`),

  get: (id: string) => api.request<Report>(`/reports/${encodeURIComponent(id)}`),

  nearby: (id: string) => api.request<NearbyReport[]>(`/reports/${encodeURIComponent(id)}/nearby`),

  verify: (id: string, note?: string) =>
    api.request<DecisionResult>(`/reports/${encodeURIComponent(id)}/verify`, {
      method: 'POST',
      json: note ? { note } : {},
    }),

  reject: (id: string, reason: string) =>
    api.request<DecisionResult>(`/reports/${encodeURIComponent(id)}/reject`, {
      method: 'POST',
      json: { reason },
    }),

  flag: (id: string, reason: string) =>
    api.request<DecisionResult>(`/reports/${encodeURIComponent(id)}/flag`, {
      method: 'POST',
      json: { reason },
    }),
};

export { query as buildQuery };
