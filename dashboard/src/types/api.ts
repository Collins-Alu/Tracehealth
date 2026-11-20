/** Shapes returned by the TraceHealth API (mirror backend/app/schemas). */

export type Role = 'REPORTER' | 'VERIFIER' | 'AGENCY_STAFF' | 'ADMINISTRATOR';
export type PollutionCategory = 'OPEN_BURNING' | 'ILLEGAL_DUMPING' | 'BLOCKED_DRAINAGE' | 'MEDICAL_WASTE' | 'OTHER';
export type ConditionCategory = 'RESPIRATORY' | 'SKIN' | 'DIARRHOEAL' | 'MALARIA' | 'INJURY' | 'INFECTION' | 'OTHER';
export type ReportStatus = 'PENDING' | 'VERIFIED' | 'REJECTED' | 'FLAGGED';
export type LinkageStatus = 'SIGNAL' | 'NO_SIGNAL' | 'INSUFFICIENT_DATA';
export type PayoutStatus = 'PENDING' | 'SUCCESS' | 'FAILED';
export type PayoutProvider = 'MOCK' | 'MPESA_DARAJA';

export const POLLUTION_CATEGORIES: PollutionCategory[] = [
  'OPEN_BURNING', 'ILLEGAL_DUMPING', 'BLOCKED_DRAINAGE', 'MEDICAL_WASTE', 'OTHER',
];
export const CONDITIONS: ConditionCategory[] = [
  'RESPIRATORY', 'SKIN', 'DIARRHOEAL', 'MALARIA', 'INJURY', 'INFECTION', 'OTHER',
];
export const ROLES: Role[] = ['REPORTER', 'VERIFIER', 'AGENCY_STAFF', 'ADMINISTRATOR'];

export interface User {
  id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  preferred_language: 'EN' | 'SW';
  roles: Role[];
  assigned_zone: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface Zone {
  code: string;
  name: string;
  latitude: number;
  longitude: number;
  radius_km: number;
}

export interface ZoneAdmin extends Zone {
  is_active: boolean;
  reports: number;
  verifiers: number;
}

export interface PayoutSummary {
  status: PayoutStatus;
  amount: string;
  currency: string;
  provider: PayoutProvider;
  is_test_payment: boolean;
  paid_at: string | null;
}

export interface Report {
  id: string;
  photo_url: string;
  latitude: number;
  longitude: number;
  category: PollutionCategory;
  description: string | null;
  captured_at: string;
  received_at: string;
  status: ReportStatus;
  sync_status: 'SUBMITTED_ONLINE' | 'SYNCED_FROM_OFFLINE';
  decision_reason: string | null;
  zone_code: string | null;
  payout: PayoutSummary | null;
}

export interface Overview {
  total: number;
  by_status: Record<ReportStatus, number>;
  verified_by_category: Record<PollutionCategory, number>;
  verified_last_7_days: number;
  top_zones: { zone_code: string | null; zone_name: string; verified: number }[];
  linkages_by_status: Record<LinkageStatus, number>;
  payouts: {
    by_status: Record<PayoutStatus, number>;
    paid_total: string;
    currency: string;
    test_payments: number;
  } | null;
}

export interface MapPoint {
  id: string;
  latitude: number;
  longitude: number;
  category: PollutionCategory;
  captured_at: string;
  zone_code: string | null;
}

export interface HeatPoint {
  latitude: number;
  longitude: number;
  weight: number;
}

export interface Trends {
  weeks: string[];
  reports: Partial<Record<PollutionCategory, number[]>>;
  visits: Partial<Record<ConditionCategory, (number | null)[]>>;
  suppressed: Partial<Record<ConditionCategory, boolean[]>>;
  small_count_threshold: number;
  notice: string;
}

export interface Linkage {
  id: string;
  status: LinkageStatus;
  insufficient_reason: string | null;
  condition_category: ConditionCategory;
  report_id: string;
  report_category: PollutionCategory;
  report_captured_at: string;
  report_zone_code: string | null;
  facility_code: string;
  facility_name: string;
  facility_area_code: string;
  distance_km: number;
  radius_km: number;
  baseline_visits: number | null;
  followup_visits: number | null;
  baseline_days: number | null;
  followup_days: number | null;
  rate_ratio: number | null;
  p_value: number | null;
  correlation_score: number | null;
  detected_at: string;
}

export interface LinkagePage extends Page<Linkage> {
  notice: string;
}

export interface Cluster {
  facility_id: string;
  facility_code: string;
  facility_name: string;
  area_code: string;
  latitude: number;
  longitude: number;
  condition_category: ConditionCategory;
  signal_reports: number;
  pollution_categories: PollutionCategory[];
  max_rate_ratio: number;
  min_p_value: number;
  latest_report_at: string;
}

export interface LinkageTrends {
  by_status: Record<LinkageStatus, number>;
  by_condition: Partial<Record<ConditionCategory, Record<LinkageStatus, number>>>;
  clusters: Cluster[];
  notice: string;
}

export interface LinkageRun {
  reports_considered: number;
  linkages: number;
  by_status: Record<LinkageStatus, number>;
}

export interface ImportProblem {
  row: number | null;
  field: string | null;
  message: string;
}

export interface ImportBatch {
  id: string;
  filename: string;
  status: 'ACCEPTED' | 'REJECTED';
  row_count: number;
  summary: {
    rows: number;
    rows_inserted: number;
    rows_updated: number;
    facilities_created: number;
    facilities_updated: number;
    small_counts: number;
  } | null;
  errors: ImportProblem[] | null;
  created_at: string;
  imported_by_name: string | null;
}

export interface ImportResult {
  batch: ImportBatch;
  linkage: LinkageRun | null;
}

export interface Facility {
  id: string;
  external_code: string;
  name: string;
  area_code: string;
  latitude: number;
  longitude: number;
  summaries: number;
  latest_period_end: string | null;
}

export interface AdminUser {
  id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  preferred_language: 'EN' | 'SW';
  is_active: boolean;
  roles: Role[];
  assigned_zone: string | null;
  agency_name: string | null;
  department: string | null;
  admin_level: number | null;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  created_at: string;
  actor_id: string | null;
  actor_name: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details: Record<string, unknown> | null;
}

export interface Setting {
  key: string;
  value: unknown;
  description: string | null;
  updated_at: string;
}

export interface Payout {
  id: string;
  report_id: string;
  report_category: PollutionCategory;
  reporter_name: string;
  phone_masked: string;
  amount: string;
  currency: string;
  provider: PayoutProvider;
  is_test_payment: boolean;
  status: PayoutStatus;
  transaction_ref: string | null;
  provider_request_id: string | null;
  failure_reason: string | null;
  attempts: number;
  created_at: string;
  last_attempt_at: string | null;
  paid_at: string | null;
}

export interface ProcessResult {
  processed: number;
  completed: number;
  accepted: number;
  failed: number;
  retry_later: number;
  not_configured: number;
}
