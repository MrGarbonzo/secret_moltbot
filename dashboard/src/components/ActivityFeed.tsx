'use client';

import { useActivity } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner } from '@/components/ui';
import type { Activity } from '@/lib/types';

function ActivityItem({ activity }: { activity: Activity }) {
  const typeColors: Record<string, 'info' | 'success' | 'warning'> = {
    post: 'success',
    comment: 'info',
    upvote: 'warning',
    downvote: 'warning',
  };

  const typeLabels: Record<string, string> = {
    post: 'Posted',
    comment: 'Commented',
    upvote: 'Upvoted',
    downvote: 'Downvoted',
  };

  const getActivityDescription = () => {
    const data = activity.data as Record<string, string | undefined>;
    return data.title || data.content || data.target_id || 'Activity';
  };

  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-100 last:border-0">
      <Badge variant={typeColors[activity.type] || 'default'} size="sm">
        {typeLabels[activity.type] || activity.type}
      </Badge>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 truncate">
          {getActivityDescription()}
        </p>
        <p className="text-xs text-gray-500">
          {new Date(activity.timestamp).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

export function ActivityFeed() {
  const { activities, isLoading, isError } = useActivity(10);

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (isError) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Recent Activity</CardTitle>
        </CardHeader>
        <div className="text-center py-8 text-red-500">
          Failed to load activity
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Activity</CardTitle>
      </CardHeader>
      {activities.length === 0 ? (
        <p className="text-center py-8 text-gray-500">No activity yet</p>
      ) : (
        <div className="divide-y divide-gray-100">
          {activities.map((activity) => (
            <ActivityItem key={activity.id} activity={activity} />
          ))}
        </div>
      )}
    </Card>
  );
}
