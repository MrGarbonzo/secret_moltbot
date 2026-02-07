'use client';

import { useStatus } from '@/lib/hooks';
import { StatusCard, ActivityFeed, AttestationCard, BirthCertificateCard } from '@/components';

export default function DashboardPage() {
  const { status } = useStatus();

  const isVerified = status?.state === 'verified';

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="text-gray-500">Monitor your autonomous SecretMolt agent</p>
        </div>
      </div>

      {isVerified ? (
        <>
          {/* Verified: full dashboard */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <StatusCard />
            <AttestationCard />
          </div>
          <BirthCertificateCard />
          <ActivityFeed />
        </>
      ) : (
        /* Not verified: just the status card (handles all states) */
        <div className="max-w-lg mx-auto">
          <StatusCard />
        </div>
      )}
    </div>
  );
}
