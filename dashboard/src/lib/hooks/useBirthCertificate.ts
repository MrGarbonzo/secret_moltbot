import useSWR from 'swr';
import { api, ApiError } from '../api';
import type { BirthCertificate } from '../types';

export function useBirthCertificate() {
  const { data, error, isLoading, mutate } = useSWR<BirthCertificate>(
    'birth-certificate',
    () => api.getBirthCertificate(),
    {
      revalidateOnFocus: false,
      shouldRetryOnError: false,
    }
  );

  const notFound = error instanceof ApiError && error.status === 404;

  return {
    certificate: data,
    isLoading,
    isError: !!error && !notFound,
    notFound,
    error,
    refresh: mutate,
  };
}
