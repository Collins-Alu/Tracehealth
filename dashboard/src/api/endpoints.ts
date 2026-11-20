/** Typed functions for every API endpoint the dashboard uses. */
import type {
  AdminUser, AuditEntry, ConditionCategory, Facility, HeatPoint, ImportBatch, ImportResult,
  Linkage, LinkagePage, LinkageRun, LinkageStatus, LinkageTrends, MapPoint, Overview, Page,
  Payout, PayoutStatus, PollutionCategory, ProcessResult, Report, ReportStatus, Role, Setting,
  TokenResponse, Trends, User, Zone, ZoneAdmin,
} from '@/types/api';

import { qs, request } from './client';

export interface ReportFilters {
  date_from?: string;
  date_to?: string;
  zone?: string;
  category?: PollutionCategory | '';
}

export const authApi = {
  login: (identifier: string, password: string) =>
    request<TokenResponse>('/auth/login', { method: 'POST', json: { identifier, password }, auth: false }),
  logout: (refresh_token: string) =>
    request<void>('/auth/logout', { method: 'POST', json: { refresh_token } }),
  me: () => request<User>('/auth/me'),
  updateMe: (body: { preferred_language: 'EN' | 'SW' }) =>
    request<User>('/auth/me', { method: 'PATCH', json: body }),
};

export const dashboardApi = {
  overview: (f: ReportFilters) => request<Overview>(`/dashboard/overview${qs({ ...f })}`),
  points: (f: ReportFilters) => request<MapPoint[]>(`/dashboard/reports${qs({ ...f })}`),
  heatmap: (f: ReportFilters) => request<HeatPoint[]>(`/dashboard/heatmap${qs({ ...f })}`),
  trends: (f: ReportFilters & { condition?: ConditionCategory | ''; area_code?: string }) =>
    request<Trends>(`/dashboard/trends${qs({ ...f })}`),
};

export const reportsApi = {
  search: (f: ReportFilters & { status?: ReportStatus | ''; limit: number; offset: number }) =>
    request<Page<Report>>(`/reports${qs({ ...f })}`),
  get: (id: string) => request<Report>(`/reports/${id}`),
  photo: (id: string) => request<Response>(`/reports/${id}/photo`, { raw: true }),
};

export const zonesApi = {
  list: () => request<Zone[]>('/zones'),
  adminList: () => request<ZoneAdmin[]>('/admin/zones'),
  create: (z: Omit<Zone, 'radius_km'> & { radius_km: number }) =>
    request<ZoneAdmin>('/admin/zones', { method: 'POST', json: z }),
  update: (code: string, z: Partial<ZoneAdmin>) =>
    request<ZoneAdmin>(`/admin/zones/${code}`, { method: 'PATCH', json: z }),
};

export const linkageApi = {
  list: (f: { status?: LinkageStatus | ''; condition?: ConditionCategory | ''; zone?: string; report_id?: string; limit: number; offset: number }) =>
    request<LinkagePage>(`/health-linkage${qs({ ...f })}`),
  trends: () => request<LinkageTrends>('/health-linkage/trends'),
  compute: () => request<LinkageRun>('/health-linkage/compute', { method: 'POST' }),
};

export const clinicApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    // 422 = file rejected with a list of problems: show it, don't throw
    return request<ImportResult>('/clinic-data/import', { method: 'POST', form, acceptStatus: [422] });
  },
  imports: () => request<ImportBatch[]>('/clinic-data/imports'),
  facilities: () => request<Facility[]>('/facilities'),
  template: () => request<Response>('/clinic-data/template.csv', { raw: true }),
};

export const adminApi = {
  users: (f: { q?: string; role?: Role | ''; active?: string; limit: number; offset: number }) =>
    request<Page<AdminUser>>(`/admin/users${qs({ ...f })}`),
  createUser: (body: Record<string, unknown>) =>
    request<AdminUser>('/admin/users', { method: 'POST', json: body }),
  updateUser: (id: string, body: Record<string, unknown>) =>
    request<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', json: body }),
  audit: (f: { action?: string; date_from?: string; date_to?: string; limit: number; offset: number }) =>
    request<Page<AuditEntry>>(`/admin/audit-logs${qs({ ...f })}`),
  settings: () => request<Setting[]>('/admin/settings'),
  updateSetting: (key: string, value: unknown) =>
    request<Setting>(`/admin/settings/${key}`, { method: 'PATCH', json: { value } }),
};

export const payoutsApi = {
  list: (f: { status?: PayoutStatus | ''; limit: number; offset: number }) =>
    request<Page<Payout>>(`/payouts${qs({ ...f })}`),
  trigger: () => request<ProcessResult>('/payouts/trigger', { method: 'POST', json: {} }),
  retry: (id: string) => request<ProcessResult>(`/payouts/${id}/retry`, { method: 'POST' }),
};

export type { Linkage };
