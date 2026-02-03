import useSWR from 'swr';
import { api } from '../api';
import type { AttestationData } from '../types';

export function useAttestation(refreshInterval = 60000) {
  const { data, error, isLoading, mutate } = useSWR<AttestationData>(
    'attestation',
    () => api.getAttestation(),
    { refreshInterval }
  );

  return {
    attestation: data,
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
