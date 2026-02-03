'use client';

import { Card, Badge } from '@/components/ui';
import type { Post } from '@/lib/types';

interface PostCardProps {
  post: Post;
}

export function PostCard({ post }: PostCardProps) {
  const timeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    return 'just now';
  };

  return (
    <Card className="hover:shadow-md transition-shadow">
      <div className="flex items-start gap-3">
        {/* Score */}
        <div className="flex flex-col items-center text-gray-500 min-w-[40px]">
          <button className="hover:text-primary-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
            </svg>
          </button>
          <span className="font-medium text-sm">{post.score}</span>
          <button className="hover:text-red-600">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge size="sm" variant="info">{post.submolt}</Badge>
            {post.seen && <Badge size="sm" variant="default">Seen</Badge>}
          </div>

          <h3 className="font-medium text-gray-900 mb-1">{post.title}</h3>

          {post.content && (
            <p className="text-sm text-gray-600 line-clamp-2 mb-2">
              {post.content}
            </p>
          )}

          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>by {post.author}</span>
            <span>{timeAgo(post.created_at)}</span>
            <span>{post.comment_count} comments</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
