import useSWR from 'swr';
import { api } from '../api';
import type { StatusResponse } from '../types';

export function useStatus(refreshInterval = 30000) {
  const { data, error, isLoading, mutate } = useSWR<StatusResponse>(
    'status',
    () => api.getStatus(),
    { refreshInterval }
  );

  return {
    status: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
