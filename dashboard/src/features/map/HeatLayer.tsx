import '@/lib/leafletGlobal';
import 'leaflet.heat';

import L from 'leaflet';
import { useEffect } from 'react';
import { useMap } from 'react-leaflet';

import type { HeatPoint } from '@/types/api';

export function HeatLayer({ points }: { points: HeatPoint[] }) {
  const map = useMap();
  useEffect(() => {
    const max = Math.max(1, ...points.map((p) => p.weight));
    const layer = L.heatLayer(
      points.map((p) => [p.latitude, p.longitude, p.weight / max] as [number, number, number]),
      { radius: 28, blur: 22, minOpacity: 0.35, gradient: { 0.3: '#0F6E64', 0.6: '#E89B2E', 1: '#B42318' } },
    ).addTo(map);
    return () => {
      map.removeLayer(layer);
    };
  }, [map, points]);
  return null;
}
