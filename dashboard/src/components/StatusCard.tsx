'use client';

import { useState } from 'react';
import { useStatus } from '@/lib/hooks';
import { api } from '@/lib/api';
import { Card, CardHeader, CardTitle, Badge, Button, Spinner } from '@/components/ui';

export function StatusCard() {
  const { status, isLoading, isError, refresh } = useStatus();
  const [checking, setChecking] = useState(false);
  const [checkMessage, setCheckMessage] = useState('');

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
          Failed to connect to agent
        </div>
      </Card>
    );
  }

  // ── Booting ──
  if (status.state === 'booting') {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Status</CardTitle>
          <Badge variant="warning">Booting</Badge>
        </CardHeader>
        <div className="flex flex-col items-center py-8 text-gray-500">
          <Spinner />
          <p className="mt-4">Agent is starting up...</p>
        </div>
      </Card>
    );
  }

  // ── Registering ──
  if (status.state === 'registering') {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Status</CardTitle>
          <Badge variant="warning">Registering</Badge>
        </CardHeader>
        <div className="flex flex-col items-center py-8 text-gray-500">
          <Spinner />
          <p className="mt-4">Registering on Moltbook...</p>
          <p className="mt-1 text-sm">Generating API key inside TEE</p>
        </div>
      </Card>
    );
  }

  // ── Error ──
  if (status.state === 'error') {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Status</CardTitle>
          <Badge variant="danger">Error</Badge>
        </CardHeader>
        <div className="py-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <p className="text-red-800 font-medium">Registration failed</p>
            <p className="text-red-600 text-sm mt-1">{status.error || 'Unknown error'}</p>
          </div>
          <p className="text-gray-500 text-sm mt-3">
            Check that the agent can reach Moltbook at the configured URL. Restart the container to retry.
          </p>
        </div>
      </Card>
    );
  }

  // ── Registered (awaiting Twitter verification) ──
  if (status.state === 'registered') {
    const handleCheckVerification = async () => {
      setChecking(true);
      setCheckMessage('');
      try {
        const result = await api.checkVerification();
        setCheckMessage(result.message);
        if (result.verified) {
          // Refresh status to transition to verified view
          refresh();
        }
      } catch (err) {
        setCheckMessage('Failed to check verification. Try again.');
      } finally {
        setChecking(false);
      }
    };

    return (
      <Card>
        <CardHeader>
          <CardTitle>Agent Status</CardTitle>
          <Badge variant="warning">Awaiting Verification</Badge>
        </CardHeader>

        <div className="space-y-4">
          {/* Verification code */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-700 font-medium mb-2">Verification Code</p>
            <div className="bg-white border border-blue-300 rounded px-4 py-3 font-mono text-xl text-center select-all">
              {status.verification_code || '—'}
            </div>
          </div>

          {/* Instructions */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-3">
            <p className="font-medium text-gray-900">To activate your agent:</p>
            <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
              <li>
                Go to the claim page:{' '}
                {status.claim_url ? (
                  <a
                    href={status.claim_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:underline break-all"
                  >
                    {status.claim_url}
                  </a>
                ) : (
                  <span className="text-gray-400">Loading...</span>
                )}
              </li>
              <li>Post the verification code above on Twitter/X</li>
              <li>Come back here and click the button below</li>
            </ol>
          </div>

          {/* Check verification button */}
          <Button
            onClick={handleCheckVerification}
            isLoading={checking}
            className="w-full"
          >
            I&apos;ve posted it — check verification
          </Button>

          {/* Feedback message */}
          {checkMessage && (
            <p className={`text-sm text-center ${
              checkMessage.includes('confirmed') ? 'text-green-600' : 'text-gray-600'
            }`}>
              {checkMessage}
            </p>
          )}

          {/* Agent info */}
          <div className="pt-3 border-t border-gray-100 grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-gray-500">Agent</p>
              <p className="font-medium">{status.agent_name}</p>
            </div>
            <div>
              <p className="text-gray-500">Model</p>
              <p className="font-medium truncate">{status.model}</p>
            </div>
          </div>
        </div>
      </Card>
    );
  }

  // ── Verified (normal operation) ──
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
          <p className="font-medium">{status.karma ?? 0}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Model</p>
          <p className="font-medium text-sm truncate">{status.model}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Posts</p>
          <p className="font-medium">{status.stats?.total_posts ?? 0}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Comments</p>
          <p className="font-medium">{status.stats?.total_comments ?? 0}</p>
        </div>

        <div>
          <p className="text-sm text-gray-500">Seen Posts</p>
          <p className="font-medium">{status.stats?.seen_posts ?? 0}</p>
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
