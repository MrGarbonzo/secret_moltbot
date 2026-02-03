'use client';

import { useState } from 'react';
import { useMemory } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Button, Badge, Spinner } from '@/components/ui';
import { api } from '@/lib/api';

export function MemoryViewer() {
  const { memory, isLoading, isError, refresh } = useMemory();
  const [isClearing, setIsClearing] = useState(false);

  const handleClear = async () => {
    if (!confirm('Are you sure you want to clear all memory? This cannot be undone.')) {
      return;
    }

    setIsClearing(true);
    try {
      await api.clearMemory();
      refresh();
    } catch (error) {
      alert('Failed to clear memory');
    } finally {
      setIsClearing(false);
    }
  };

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-12">
          <Spinner size="lg" />
        </div>
      </Card>
    );
  }

  if (isError || !memory) {
    return (
      <Card>
        <div className="text-center py-12 text-red-500">
          Failed to load memory
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Stats Overview */}
      <Card>
        <CardHeader>
          <CardTitle>Memory Overview</CardTitle>
          <Button variant="danger" size="sm" onClick={handleClear} isLoading={isClearing}>
            Clear All
          </Button>
        </CardHeader>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-primary-600">{memory.seen_count}</p>
            <p className="text-sm text-gray-500">Seen Posts</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-primary-600">
              {memory.activity_stats.post || 0}
            </p>
            <p className="text-sm text-gray-500">Posts Created</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-primary-600">
              {memory.activity_stats.comment || 0}
            </p>
            <p className="text-sm text-gray-500">Comments</p>
          </div>
          <div className="text-center p-4 bg-gray-50 rounded-lg">
            <p className="text-2xl font-bold text-primary-600">
              {(memory.activity_stats.upvote || 0) + (memory.activity_stats.downvote || 0)}
            </p>
            <p className="text-sm text-gray-500">Votes Cast</p>
          </div>
        </div>
      </Card>

      {/* Personality Notes */}
      <Card>
        <CardHeader>
          <CardTitle>Personality Notes</CardTitle>
        </CardHeader>
        {memory.personality_notes.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No personality notes yet</p>
        ) : (
          <ul className="space-y-2">
            {memory.personality_notes.map((note, index) => (
              <li key={index} className="flex items-start gap-2">
                <Badge size="sm" variant="info">{index + 1}</Badge>
                <span className="text-sm text-gray-700">{note}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <CardTitle>Activity Log</CardTitle>
        </CardHeader>
        {memory.recent_activity.length === 0 ? (
          <p className="text-gray-500 text-center py-4">No activity recorded</p>
        ) : (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {memory.recent_activity.map((activity) => {
              const data = activity.data as Record<string, string | undefined>;
              return (
                <div
                  key={activity.id}
                  className="flex items-center gap-3 p-2 bg-gray-50 rounded text-sm"
                >
                  <Badge size="sm" variant={activity.type === 'post' ? 'success' : 'info'}>
                    {activity.type}
                  </Badge>
                  <span className="flex-1 truncate text-gray-700">
                    {data.title || data.content || data.target_id || 'Activity'}
                  </span>
                  <span className="text-xs text-gray-400">
                    {new Date(activity.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
