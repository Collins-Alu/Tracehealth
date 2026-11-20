/**
 * Page frame: navigation on the left (top on narrow screens), content on the
 * right. Administration pages appear only for administrators.
 */
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet } from 'react-router';

import { useAuth } from '@/auth/AuthContext';

import { LanguageSwitch } from './LanguageSwitch';

const MAIN = [
  { to: '/', key: 'nav.overview', end: true },
  { to: '/map', key: 'nav.map' },
  { to: '/trends', key: 'nav.trends' },
  { to: '/reports', key: 'nav.reports' },
];
const ADMIN = [
  { to: '/clinic-data', key: 'nav.clinicImport' },
  { to: '/payouts', key: 'nav.payouts' },
  { to: '/users', key: 'nav.users' },
  { to: '/audit', key: 'nav.audit' },
  { to: '/settings', key: 'nav.settings' },
];

function Item({ to, label, end, onClick }: { to: string; label: string; end?: boolean; onClick: () => void }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `block rounded-md px-3 py-2 ${
          isActive ? 'bg-teal text-white' : 'text-ink hover:bg-teal-soft'
        }`
      }
    >
      {label}
    </NavLink>
  );
}

export function Layout() {
  const { t } = useTranslation();
  const { user, isAdmin, signOut } = useAuth();
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[15rem_1fr]">
      <header className="flex items-center justify-between border-b border-line bg-paper px-4 py-3 lg:hidden">
        <span className="text-lg font-semibold text-teal-dark">{t('app.name')}</span>
        <button className="btn-quiet" aria-expanded={open} onClick={() => setOpen((v) => !v)}>
          {open ? t('common.close') : t('nav.menu')}
        </button>
      </header>
      <aside
        className={`${open ? 'block' : 'hidden'} border-r border-line bg-paper lg:sticky lg:top-0 lg:block lg:h-screen`}
      >
        <nav className="flex h-full flex-col gap-1 p-4" aria-label="Main">
          <div className="mb-4 hidden lg:block">
            <div className="text-xl font-semibold text-teal-dark">{t('app.name')}</div>
            <p className="mt-1 text-sm text-muted">{t('app.tagline')}</p>
          </div>
          {MAIN.map((i) => (
            <Item key={i.to} to={i.to} end={i.end} label={t(i.key)} onClick={close} />
          ))}
          {isAdmin ? (
            <>
              <p className="mt-5 mb-1 px-3 text-sm text-muted">{t('nav.admin')}</p>
              {ADMIN.map((i) => (
                <Item key={i.to} to={i.to} label={t(i.key)} onClick={close} />
              ))}
            </>
          ) : null}
          <div className="mt-auto space-y-3 border-t border-line pt-4">
            <div className="px-3 text-sm">
              <div className="font-medium">{user?.full_name}</div>
              <div className="text-muted">{user?.roles.map((r) => t(`roles.${r}`)).join(', ')}</div>
            </div>
            <LanguageSwitch />
            <button className="btn-quiet w-full justify-start" onClick={signOut}>
              {t('nav.signOut')}
            </button>
          </div>
        </nav>
      </aside>
      <main className="min-w-0 px-4 py-6 sm:px-8">
        <Outlet />
      </main>
    </div>
  );
}
