import { useContext } from 'react';

import { SyncContextInternal } from './SyncContext';

/** Like useSync(), but returns null outside the provider (e.g. in tests). */
export function useOptionalSync() {
  return useContext(SyncContextInternal);
}
