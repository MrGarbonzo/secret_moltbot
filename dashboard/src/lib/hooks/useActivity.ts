import useSWR from 'swr';
import { api } from '../api';
import type { ActivityResponse } from '../types';

export function useActivity(limit = 20, refreshInterval = 10000) {
  const { data, error, isLoading, mutate } = useSWR<ActivityResponse>(
    ['activity', limit],
    () => api.getActivity(limit),
    { refreshInterval }
  );

  return {
    activities: data?.activities || [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
