/** Shapes returned by the TraceHealth API (mirror backend/app/schemas). */

export type Role = 'REPORTER' | 'VERIFIER' | 'AGENCY_STAFF' | 'ADMINISTRATOR';

export type PollutionCategory =
  | 'OPEN_BURNING'
  | 'ILLEGAL_DUMPING'
  | 'BLOCKED_DRAINAGE'
  | 'MEDICAL_WASTE'
  | 'OTHER';

export const POLLUTION_CATEGORIES: PollutionCategory[] = [
  'OPEN_BURNING',
  'ILLEGAL_DUMPING',
  'BLOCKED_DRAINAGE',
  'MEDICAL_WASTE',
  'OTHER',
];

export type ReportStatus = 'PENDING' | 'VERIFIED' | 'REJECTED' | 'FLAGGED';
export type SyncStatus = 'SUBMITTED_ONLINE' | 'SYNCED_FROM_OFFLINE';
export type PayoutStatus = 'PENDING' | 'SUCCESS' | 'FAILED';

export interface User {
  id: string;
  full_name: string;
  phone_number: string;
  email: string | null;
  preferred_language: 'EN' | 'SW';
  roles: Role[];
  assigned_zone: string | null;
  payout_phone: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

export interface PayoutSummary {
  status: PayoutStatus;
  amount: string;
  currency: string;
  provider: 'MPESA_DARAJA' | 'MOCK';
  is_test_payment: boolean;
  paid_at: string | null;
}

export interface Report {
  id: string;
  client_report_id: string;
  photo_url: string;
  latitude: number;
  longitude: number;
  category: PollutionCategory;
  description: string | null;
  captured_at: string;
  received_at: string;
  status: ReportStatus;
  sync_status: SyncStatus;
  decision_reason: string | null;
  payout: PayoutSummary | null;
}

export interface ReportPage {
  items: Report[];
  total: number;
  limit: number;
  offset: number;
}

export interface SubmitResult {
  report: Report;
  already_received: boolean;
}

export interface RegisterInput {
  full_name: string;
  phone_number: string;
  password: string;
  email?: string;
  preferred_language: 'EN' | 'SW';
  accept_privacy_notice: boolean;
  payout_consent: boolean;
}
