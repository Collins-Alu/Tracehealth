/** User and role management (administrators). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { adminApi } from '@/api/endpoints';
import { useAuth } from '@/auth/AuthContext';
import { PageHeader } from '@/components/PageHeader';
import { Pagination } from '@/components/Pagination';
import { Empty, ErrorNote, Loading, Notice } from '@/components/State';
import { type AdminUser, ROLES, type Role } from '@/types/api';

import { UserDialog } from './UserDialog';

const PAGE = 25;

export function UsersPage() {
  const { t } = useTranslation();
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [q, setQ] = useState('');
  const [role, setRole] = useState<Role | ''>('');
  const [offset, setOffset] = useState(0);
  const [editing, setEditing] = useState<AdminUser | null>(null);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const users = useQuery({ queryKey: ['users', q, role, offset], queryFn: () => adminApi.users({ q, role, limit: PAGE, offset }) });
  const toggleActive = useMutation({
    mutationFn: (u: AdminUser) => adminApi.updateUser(u.id, { is_active: !u.is_active }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); setMessage(t('users.updatedMsg')); },
  });

  const closeDialog = () => { setEditing(null); setCreating(false); };

  return (
    <>
      <PageHeader title={t('users.title')} actions={<button className="btn-primary" onClick={() => setCreating(true)}>{t('users.add')}</button>} />
      <form className="mb-4 flex flex-wrap items-end gap-3" onSubmit={(e) => e.preventDefault()}>
        <label className="w-72"><span className="label">{t('common.search')}</span>
          <input className="field" type="search" placeholder={t('users.searchPlaceholder')} value={q} onChange={(e) => { setQ(e.target.value); setOffset(0); }} /></label>
        <label className="w-52"><span className="label">{t('users.roles')}</span>
          <select className="field" value={role} onChange={(e) => { setRole(e.target.value as Role | ''); setOffset(0); }}>
            <option value="">{t('common.all')}</option>
            {ROLES.map((r) => <option key={r} value={r}>{t(`roles.${r}`)}</option>)}
          </select></label>
      </form>
      {message ? <div className="mb-4"><Notice tone="ok">{message}</Notice></div> : null}
      {toggleActive.isError ? <div className="mb-4"><ErrorNote error={toggleActive.error} /></div> : null}
      {users.isLoading ? <Loading /> : null}
      {users.isError ? <ErrorNote error={users.error} onRetry={() => users.refetch()} /> : null}
      {users.data ? (
        users.data.items.length ? (
          <div className="panel relative overflow-x-auto">
            <table className="table">
              <thead>
                <tr><th>{t('users.name')}</th><th>{t('users.phone')}</th><th>{t('users.roles')}</th><th>{t('common.status')}</th><th><span className="sr-only">{t('common.actions')}</span></th></tr>
              </thead>
              <tbody>
                {users.data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}{u.agency_name ? <span className="block text-xs text-muted">{u.agency_name}</span> : null}</td>
                    <td className="tabular-nums">{u.phone_number}</td>
                    <td>{u.roles.map((r) => t(`roles.${r}`)).join(', ')}{u.assigned_zone ? <span className="block text-xs text-muted">{u.assigned_zone}</span> : null}</td>
                    <td className={u.is_active ? 'text-ok' : 'text-muted'}>{u.is_active ? t('users.active') : t('users.inactive')}</td>
                    <td className="text-right whitespace-nowrap">
                      <button className="btn-quiet" onClick={() => { setMessage(null); setEditing(u); }}>{t('common.edit')}</button>
                      {u.id !== me?.id ? (
                        <button
                          className="btn-quiet"
                          onClick={() => {
                            if (!u.is_active || window.confirm(t('users.confirmDeactivate', { name: u.full_name }))) toggleActive.mutate(u);
                          }}
                        >
                          {u.is_active ? t('users.deactivate') : t('users.reactivate')}
                        </button>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="px-4 pb-3"><Pagination total={users.data.total} limit={PAGE} offset={offset} onChange={setOffset} /></div>
          </div>
        ) : <Empty>{t('users.empty')}</Empty>
      ) : null}
      {creating || editing ? (
        <UserDialog key={editing?.id ?? 'new'} user={editing} open onClose={closeDialog} onSaved={(m) => { closeDialog(); setMessage(m); }} />
      ) : null}
    </>
  );
}
