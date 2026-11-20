import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Navigate } from 'react-router';

import { NoDashboardAccess, useAuth } from '@/auth/AuthContext';
import { LanguageSwitch } from '@/components/LanguageSwitch';
import { errorText } from '@/components/State';

export function LoginPage() {
  const { t } = useTranslation();
  const { user, signIn } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(identifier.trim(), password);
    } catch (err) {
      setError(err instanceof NoDashboardAccess ? t('login.noAccess') : errorText(err, t));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden flex-col justify-end bg-teal-dark p-12 text-white lg:flex">
        <div className="text-5xl font-semibold tracking-tight">{t('app.name')}</div>
        <p className="mt-4 max-w-md text-lg text-teal-soft">{t('login.intro')}</p>
      </section>
      <section className="flex items-center justify-center p-6">
        <form onSubmit={submit} className="w-full max-w-sm space-y-4" aria-describedby={error ? 'login-error' : undefined}>
          <div className="text-2xl font-semibold text-teal-dark lg:hidden">{t('app.name')}</div>
          <h1 className="text-xl">{t('login.title')}</h1>
          <label className="block">
            <span className="label">{t('login.identifier')}</span>
            <input className="field" autoComplete="username" required value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
          </label>
          <label className="block">
            <span className="label">{t('login.password')}</span>
            <input className="field" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          {error ? (
            <p id="login-error" role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-danger">
              {error}
            </p>
          ) : null}
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? t('login.signingIn') : t('login.submit')}
          </button>
          <LanguageSwitch />
        </form>
      </section>
    </div>
  );
}
