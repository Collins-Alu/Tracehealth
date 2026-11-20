/** Create or edit a user. Role-specific fields appear only for those roles. */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { adminApi, zonesApi } from '@/api/endpoints';
import { Dialog } from '@/components/Dialog';
import { errorText } from '@/components/State';
import { type AdminUser, ROLES, type Role } from '@/types/api';

export function UserDialog({ user, open, onClose, onSaved }: { user: AdminUser | null; open: boolean; onClose: () => void; onSaved: (msg: string) => void }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const zones = useQuery({ queryKey: ['zones'], queryFn: zonesApi.list, staleTime: 300_000 });
  const [name, setName] = useState(user?.full_name ?? '');
  const [phone, setPhone] = useState(user?.phone_number ?? '');
  const [email, setEmail] = useState(user?.email ?? '');
  const [roles, setRoles] = useState<Role[]>(user?.roles ?? ['VERIFIER']);
  const [zone, setZone] = useState(user?.assigned_zone ?? '');
  const [agency, setAgency] = useState(user?.agency_name ?? '');
  const [department, setDepartment] = useState(user?.department ?? '');
  const [password, setPassword] = useState('');
  const [language, setLanguage] = useState<'EN' | 'SW'>(user?.preferred_language ?? 'EN');

  const save = useMutation({
    mutationFn: () => {
      const body: Record<string, unknown> = {
        full_name: name.trim(),
        email: email.trim() || null,
        roles,
        preferred_language: language,
      };
      if (roles.includes('VERIFIER')) body.assigned_zone = zone || null;
      if (roles.includes('AGENCY_STAFF')) {
        body.agency_name = agency.trim() || null;
        body.department = department.trim() || null;
      }
      if (password) body.password = password;
      if (user) return adminApi.updateUser(user.id, body);
      return adminApi.createUser({ ...body, phone_number: phone.trim(), password });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      onSaved(user ? t('users.updatedMsg') : t('users.created'));
    },
  });

  const toggle = (r: Role) => setRoles((cur) => (cur.includes(r) ? cur.filter((x) => x !== r) : [...cur, r]));
  const submit = (e: FormEvent) => { e.preventDefault(); save.mutate(); };

  return (
    <Dialog open={open} onClose={onClose} title={user ? t('users.editTitle', { name: user.full_name }) : t('users.addTitle')}>
      <form onSubmit={submit} className="space-y-4">
        <label className="block"><span className="label">{t('users.name')}</span>
          <input className="field" required minLength={2} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <label className="block"><span className="label">{t('users.phone')}</span>
          <input className="field" required disabled={!!user} value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+2547…" /></label>
        <label className="block"><span className="label">{t('users.email')}</span>
          <input className="field" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <fieldset>
          <legend className="label">{t('users.roles')}</legend>
          <div className="flex flex-wrap gap-4">
            {ROLES.map((r) => (
              <label key={r} className="flex items-center gap-2">
                <input type="checkbox" checked={roles.includes(r)} onChange={() => toggle(r)} className="h-4 w-4 accent-teal" />
                {t(`roles.${r}`)}
              </label>
            ))}
          </div>
        </fieldset>
        {roles.includes('VERIFIER') ? (
          <label className="block"><span className="label">{t('users.zone')}</span>
            <select className="field" value={zone} onChange={(e) => setZone(e.target.value)}>
              <option value="">{t('users.anyZone')}</option>
              {zones.data?.map((z) => <option key={z.code} value={z.code}>{z.name}</option>)}
            </select></label>
        ) : null}
        {roles.includes('AGENCY_STAFF') ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block"><span className="label">{t('users.agency')}</span>
              <input className="field" required value={agency} onChange={(e) => setAgency(e.target.value)} /></label>
            <label className="block"><span className="label">{t('users.department')}</span>
              <input className="field" value={department} onChange={(e) => setDepartment(e.target.value)} /></label>
          </div>
        ) : null}
        <label className="block"><span className="label">{t('nav.language')}</span>
          <select className="field" value={language} onChange={(e) => setLanguage(e.target.value as 'EN' | 'SW')}>
            <option value="EN">English</option><option value="SW">Kiswahili</option>
          </select></label>
        <label className="block"><span className="label">{user ? t('users.newPassword') : t('users.password')}</span>
          <input className="field" type="password" autoComplete="new-password" required={!user} value={password} onChange={(e) => setPassword(e.target.value)} />
          <span className="mt-1 block text-sm text-muted">{t('users.passwordHelp')}</span></label>
        {save.isError ? <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-danger">{errorText(save.error, t)}</p> : null}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
          <button className="btn-primary" disabled={save.isPending || roles.length === 0}>{user ? t('common.save') : t('common.create')}</button>
        </div>
      </form>
    </Dialog>
  );
}
