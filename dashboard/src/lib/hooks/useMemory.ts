import useSWR from 'swr';
import { api } from '../api';
import type { MemoryResponse } from '../types';

export function useMemory(refreshInterval = 30000) {
  const { data, error, isLoading, mutate } = useSWR<MemoryResponse>(
    'memory',
    () => api.getMemory(),
    { refreshInterval }
  );

  return {
    memory: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
