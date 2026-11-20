import '@fontsource-variable/public-sans';
import './index.css';
import './i18n';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';

import { API_URL, ApiError } from '@/api/client';
import { AuthProvider } from '@/auth/AuthContext';

import { App } from './App';

// Wake the API early: free hosting puts it to sleep when idle, and it takes
// up to a minute to start. By the time someone has typed their password it is up.
fetch(`${API_URL}/health`).catch(() => undefined);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      refetchOnWindowFocus: false,
      // don't retry permission or validation errors: they won't fix themselves
      retry: (count, error) => !(error instanceof ApiError && error.status < 500) && count < 2,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
