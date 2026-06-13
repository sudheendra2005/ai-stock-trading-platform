const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();

const normalizeApiBase = (url) => {
  if (!url || url === '/api') return '';
  return url.replace(/\/api\/?$/, '').replace(/\/$/, '');
};

export const API_BASE = normalizeApiBase(
  configuredApiUrl || (import.meta.env.PROD ? '' : 'http://localhost:8000')
);
