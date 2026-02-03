import useSWR from 'swr';
import { api } from '../api';
import type { ConfigResponse } from '../types';

export function useConfig() {
  const { data, error, isLoading, mutate } = useSWR<ConfigResponse>(
    'config',
    () => api.getConfig()
  );

  return {
    config: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
