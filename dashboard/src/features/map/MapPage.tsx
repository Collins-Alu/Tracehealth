/**
 * Pollution map (FR 4.1): verified reports on OpenStreetMap, as markers or as
 * a density heatmap, filtered by date, zone and type.
 */
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet';

import { dashboardApi, type ReportFilters } from '@/api/endpoints';
import { Filters } from '@/components/Filters';
import { PageHeader } from '@/components/PageHeader';
import { ErrorNote } from '@/components/State';
import { CATEGORY_COLOURS } from '@/lib/categories';
import { formatDate } from '@/lib/format';
import { type MapPoint, POLLUTION_CATEGORIES } from '@/types/api';

import { HeatLayer } from './HeatLayer';

const NAIROBI: [number, number] = [-1.2921, 36.8219];

function FitTo({ points }: { points: MapPoint[] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      map.fitBounds(points.map((p) => [p.latitude, p.longitude] as [number, number]), { padding: [40, 40], maxZoom: 15 });
    }
  }, [map, points]);
  return null;
}

export function MapPage() {
  const { t, i18n } = useTranslation();
  const [filters, setFilters] = useState<ReportFilters>({});
  const [mode, setMode] = useState<'markers' | 'heat'>('markers');
  const points = useQuery({ queryKey: ['points', filters], queryFn: () => dashboardApi.points(filters) });
  const heat = useQuery({ queryKey: ['heat', filters], queryFn: () => dashboardApi.heatmap(filters), enabled: mode === 'heat' });

  return (
    <>
      <PageHeader title={t('map.title')} intro={t('map.verifiedOnly')} />
      <div className="mb-4">
        <Filters value={filters} onChange={setFilters}>
          <div role="group" aria-label={t('map.title')} className="flex overflow-hidden rounded-md border border-teal">
            {(['markers', 'heat'] as const).map((m) => (
              <button
                key={m}
                aria-pressed={mode === m}
                onClick={() => setMode(m)}
                className={`min-h-10 px-4 ${mode === m ? 'bg-teal text-white' : 'bg-paper text-teal'}`}
              >
                {m === 'markers' ? t('map.markers') : t('map.heatmap')}
              </button>
            ))}
          </div>
        </Filters>
      </div>
      {points.isError ? <ErrorNote error={points.error} onRetry={() => points.refetch()} /> : null}
      <p className="mb-2 text-sm text-muted" aria-live="polite">
        {points.data ? (points.data.length ? t('map.count', { count: points.data.length }) : t('map.empty')) : ''}
      </p>
      <div className="h-[65vh] overflow-hidden rounded-lg border border-line" data-testid="map">
        <MapContainer center={NAIROBI} zoom={12} className="h-full w-full" scrollWheelZoom>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {points.data ? <FitTo points={points.data} /> : null}
          {mode === 'markers'
            ? points.data?.map((p) => (
                <CircleMarker
                  key={p.id}
                  center={[p.latitude, p.longitude]}
                  radius={8}
                  pathOptions={{ color: '#FFFFFF', weight: 2, fillColor: CATEGORY_COLOURS[p.category], fillOpacity: 0.95 }}
                >
                  <Popup>
                    <strong>{t(`categories.${p.category}`)}</strong>
                    <br />
                    {formatDate(p.captured_at, i18n.language, true)}
                    <br />
                    <Link to={`/reports?open=${p.id}`}>{t('map.openReport')}</Link>
                  </Popup>
                </CircleMarker>
              ))
            : heat.data ? <HeatLayer points={heat.data} /> : null}
        </MapContainer>
      </div>
      {mode === 'markers' ? (
        <ul className="mt-3 flex flex-wrap gap-4 text-sm" aria-label={t('common.category')}>
          {POLLUTION_CATEGORIES.map((c) => (
            <li key={c} className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full" style={{ background: CATEGORY_COLOURS[c] }} />
              {t(`categories.${c}`)}
            </li>
          ))}
        </ul>
      ) : null}
    </>
  );
}
