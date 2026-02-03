import useSWR from 'swr';
import { api } from '../api';
import type { FeedResponse } from '../types';

export function useFeed(
  sort = 'hot',
  limit = 25,
  submolt?: string,
  refreshInterval = 30000
) {
  const { data, error, isLoading, mutate } = useSWR<FeedResponse>(
    ['feed', sort, limit, submolt],
    () => api.getFeed(sort, limit, submolt),
    { refreshInterval }
  );

  return {
    posts: data?.posts || [],
    isLoading,
    isError: !!error,
    error,
    refresh: mutate,
  };
}
