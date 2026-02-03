'use client';

import { useStatus } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner } from '@/components/ui';

export function StatusCard() {
  const { status, isLoading, isError } = useStatus();

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (isError || !status) {
    return (
      <Card>
        <div className="text-center py-8 text-red-500">
          Failed to load status
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Status</CardTitle>
        <Badge variant={status.online ? 'success' : 'danger'}>
          {status.online ? 'Online' : 'Offline'}
        </Badge>
      </CardHeader>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-gray-500">State</p>
          <p className="font-medium">
            {status.paused ? (
              <span className="text-yellow-600">Paused</span>
            ) : (
              <span className="text-green-600">Active</span>
            )}
          </p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Karma</p>
          <p className="font-medium">{status.karma}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Model</p>
          <p className="font-medium text-sm truncate">{status.model}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Posts</p>
          <p className="font-medium">{status.stats.total_posts}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Comments</p>
          <p className="font-medium">{status.stats.total_comments}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Seen Posts</p>
          <p className="font-medium">{status.stats.seen_posts}</p>
        </div>
      </div>

      {status.last_heartbeat && (
        <div className="mt-4 pt-4 border-t border-gray-100">
          <p className="text-xs text-gray-500">
            Last heartbeat: {new Date(status.last_heartbeat).toLocaleString()}
          </p>
        </div>
      )}
    </Card>
  );
}
