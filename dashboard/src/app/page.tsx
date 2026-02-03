'use client';

import { StatusCard, ActivityFeed, AttestationCard } from '@/components';

export default function DashboardPage() {
  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Monitor your autonomous SecretMolt agent</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <StatusCard />
        <AttestationCard />
      </div>

      <ActivityFeed />
    </div>
  );
}
