'use client';

import { useState } from 'react';
import { useFeed } from '@/lib/hooks';
import { PostCard } from '@/components';
import { Button, Spinner } from '@/components/ui';

export default function FeedPage() {
  const [sort, setSort] = useState<'hot' | 'new' | 'top'>('hot');
  const { posts, isLoading, isError, refresh } = useFeed(sort, 25);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Moltbook Feed</h1>
          <p className="text-gray-500">What the agent sees from Moltbook</p>
        </div>
        <Button onClick={() => refresh()} variant="secondary" size="sm">
          Refresh
        </Button>
      </div>

      {/* Sort tabs */}
      <div className="flex gap-2 border-b border-gray-200 pb-2">
        {(['hot', 'new', 'top'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setSort(s)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg transition-colors ${
              sort === s
                ? 'bg-primary-100 text-primary-700'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </button>
        ))}
      </div>

      {/* Posts */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      ) : isError ? (
        <div className="text-center py-12 text-red-500">
          Failed to load feed. Make sure the agent is running.
        </div>
      ) : posts.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          No posts found
        </div>
      ) : (
        <div className="space-y-4">
          {posts.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </div>
  );
}
