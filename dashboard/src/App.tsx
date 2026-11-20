/** Routes. Every page needs a dashboard role; administration pages need ADMINISTRATOR. */
import { lazy, type ReactNode, Suspense } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router';
import { useTranslation } from 'react-i18next';

import { useAuth } from '@/auth/AuthContext';
import { Layout } from '@/components/Layout';
import { LoginPage } from '@/features/auth/LoginPage';
import { Loading } from '@/components/State';

// Pages load on demand, so the map and chart libraries only download when needed
const AuditPage = lazy(() => import('@/features/audit/AuditPage').then((m) => ({ default: m.AuditPage })));
const ClinicImportPage = lazy(() => import('@/features/clinic-import/ClinicImportPage').then((m) => ({ default: m.ClinicImportPage })));
const MapPage = lazy(() => import('@/features/map/MapPage').then((m) => ({ default: m.MapPage })));
const OverviewPage = lazy(() => import('@/features/overview/OverviewPage').then((m) => ({ default: m.OverviewPage })));
const PayoutsPage = lazy(() => import('@/features/payouts/PayoutsPage').then((m) => ({ default: m.PayoutsPage })));
const ReportsPage = lazy(() => import('@/features/reports/ReportsPage').then((m) => ({ default: m.ReportsPage })));
const SettingsPage = lazy(() => import('@/features/settings/SettingsPage').then((m) => ({ default: m.SettingsPage })));
const TrendsPage = lazy(() => import('@/features/trends/TrendsPage').then((m) => ({ default: m.TrendsPage })));
const UsersPage = lazy(() => import('@/features/users/UsersPage').then((m) => ({ default: m.UsersPage })));

function RequireUser({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const location = useLocation();
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return <>{children}</>;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth();
  return isAdmin ? <>{children}</> : <Navigate to="/" replace />;
}

function NotFound() {
  const { t } = useTranslation();
  return <p className="text-muted">{t('common.notFound')}</p>;
}

export function App() {
  return (
    <Suspense fallback={<Loading />}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireUser><Layout /></RequireUser>}>
        <Route index element={<OverviewPage />} />
        <Route path="map" element={<MapPage />} />
        <Route path="trends" element={<TrendsPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="clinic-data" element={<AdminOnly><ClinicImportPage /></AdminOnly>} />
        <Route path="payouts" element={<AdminOnly><PayoutsPage /></AdminOnly>} />
        <Route path="users" element={<AdminOnly><UsersPage /></AdminOnly>} />
        <Route path="audit" element={<AdminOnly><AuditPage /></AdminOnly>} />
        <Route path="settings" element={<AdminOnly><SettingsPage /></AdminOnly>} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
    </Suspense>
  );
}
