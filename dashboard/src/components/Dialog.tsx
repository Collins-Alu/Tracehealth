/** Accessible modal dialog built on the native <dialog> element. */
import { type ReactNode, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';

export function Dialog({
  open, title, onClose, children, wide,
}: { open: boolean; title: string; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const { t } = useTranslation();

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (open && !el.open) el.showModal?.();
    if (!open && el.open) el.close?.();
  }, [open]);

  if (!open) return null;
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      aria-label={title}
      className={`m-auto w-[calc(100%-2rem)] ${wide ? 'max-w-3xl' : 'max-w-lg'} rounded-lg border border-line bg-paper p-0 text-ink backdrop:bg-ink/40`}
    >
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <h2>{title}</h2>
        <button className="btn-quiet" onClick={onClose}>
          {t('common.close')}
        </button>
      </div>
      <div className="max-h-[75vh] overflow-y-auto p-5">{children}</div>
    </dialog>
  );
}
