'use client';

import { MemoryViewer } from '@/components';

export default function MemoryPage() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Agent Memory</h1>
        <p className="text-gray-500">View and manage the agent&apos;s persistent state</p>
      </div>

      <MemoryViewer />
    </div>
  );
}
