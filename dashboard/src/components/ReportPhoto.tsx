/** Report photos need the login token, so they are fetched and shown as a blob. */
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { reportsApi } from '@/api/endpoints';

export function ReportPhoto({ reportId, alt }: { reportId: string; alt: string }) {
  const { t } = useTranslation();
  const blob = useQuery({
    queryKey: ['photo', reportId],
    queryFn: async () => (await reportsApi.photo(reportId)).blob(),
    staleTime: Infinity,
  });
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!blob.data) return;
    const u = URL.createObjectURL(blob.data);
    setUrl(u);
    return () => URL.revokeObjectURL(u);
  }, [blob.data]);

  if (blob.isError) {
    return <div className="flex aspect-[4/3] items-center justify-center rounded-md bg-mist text-muted">{t('reports.photoMissing')}</div>;
  }
  return url ? (
    <img src={url} alt={alt} className="aspect-[4/3] w-full rounded-md bg-mist object-cover" />
  ) : (
    <div className="aspect-[4/3] w-full animate-pulse rounded-md bg-mist" />
  );
}
