// API fetch wrapper with error handling

const API_URL = '/api/proxy';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text();
    throw new ApiError(errorText || response.statusText, response.status);
  }
  return response.json();
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const url = `${API_URL}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  return handleResponse<T>(response);
}

// API methods
// NOTE: This is a MONITORING-ONLY API. Control endpoints have been removed
// to ensure the agent is provably autonomous.
export const api = {
  // Status
  getStatus: () => fetchApi<import('./types').StatusResponse>('/status'),

  // Activity
  getActivity: (limit = 20) =>
    fetchApi<import('./types').ActivityResponse>(`/activity?limit=${limit}`),

  // Feed
  getFeed: (sort = 'hot', limit = 25, submolt?: string) => {
    let url = `/feed?sort=${sort}&limit=${limit}`;
    if (submolt) url += `&submolt=${submolt}`;
    return fetchApi<import('./types').FeedResponse>(url);
  },

  // Memory (read-only)
  getMemory: () => fetchApi<import('./types').MemoryResponse>('/memory'),

  // Config (read-only)
  getConfig: () => fetchApi<import('./types').ConfigResponse>('/config'),

  // Attestation
  getAttestation: () => fetchApi<import('./types').AttestationData>('/attestation'),

  // Actions (preview only - does not post)
  triggerHeartbeat: () =>
    fetchApi<import('./types').HeartbeatResult>('/heartbeat', { method: 'POST' }),

  generateContent: (topic?: string) =>
    fetchApi<import('./types').GeneratedContent>(
      `/generate${topic ? `?topic=${encodeURIComponent(topic)}` : ''}`,
      { method: 'POST' }
    ),
};
