import { File } from 'expo-file-system';

import { UPLOAD_TIMEOUT_MS } from '@/config';
import type { QueuedReport } from '@/offline/types';

import { api } from './index';
import type { Report, ReportPage, SubmitResult } from './types';

export const reportsApi = {
  myReports: (limit = 20, offset = 0) =>
    api.request<ReportPage>(`/reports/my-reports?limit=${limit}&offset=${offset}`),

  get: (id: string) => api.request<Report>(`/reports/${encodeURIComponent(id)}`),

  /**
   * Sends a queued report. Keyed by the id the phone generated, so sending
   * the same report twice is harmless: the server returns the first copy.
   */
  sync: (item: QueuedReport) => {
    const form = new FormData();
    form.append('category', item.category);
    form.append('latitude', String(item.latitude));
    form.append('longitude', String(item.longitude));
    form.append('captured_at', item.capturedAt);
    form.append('created_offline', item.createdOffline ? 'true' : 'false');
    if (item.description) form.append('description', item.description);
    // Expo's fetch (SDK 54+) needs a real File; the old React Native
    // { uri, name, type } object is rejected with "Unsupported FormDataPart"
    form.append('photo', new File(item.photoUri), 'photo.jpg');
    return api.request<SubmitResult>(`/reports/${item.clientReportId}/sync`, {
      method: 'POST',
      form,
      timeoutMs: UPLOAD_TIMEOUT_MS,
    });
  },
};
