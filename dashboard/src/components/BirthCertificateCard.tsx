'use client';

import { useBirthCertificate } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner } from '@/components/ui';

export function BirthCertificateCard() {
  const { certificate, isLoading, notFound } = useBirthCertificate();

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (notFound || !certificate) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Birth Certificate</CardTitle>
          <Badge variant="warning" size="sm">Unavailable</Badge>
        </CardHeader>
        <p className="text-sm text-gray-500">
          No birth certificate found. The agent may not have completed registration yet,
          or it was registered before birth certificates were implemented.
        </p>
      </Card>
    );
  }

  const qualityVariant = certificate.attestation_snapshot.quality === 'high'
    ? 'success' : certificate.attestation_snapshot.quality === 'none'
    ? 'danger' : 'warning';

  return (
    <Card>
      <CardHeader>
        <CardTitle>Birth Certificate</CardTitle>
        <div className="flex items-center gap-2">
          {certificate.self_created && (
            <Badge variant="success" size="sm">Self-Created</Badge>
          )}
          <Badge variant={qualityVariant} size="sm">
            {certificate.attestation_snapshot.quality.toUpperCase()} at birth
          </Badge>
        </div>
      </CardHeader>

      <div className="space-y-3">
        <div>
          <p className="text-xs text-gray-500">API Key Hash</p>
          <p className="font-mono text-xs truncate" title={certificate.api_key_hash}>
            {certificate.api_key_hash.slice(0, 16)}...{certificate.api_key_hash.slice(-16)}
          </p>
        </div>

        <div>
          <p className="text-xs text-gray-500">Born</p>
          <p className="text-sm text-gray-700">
            {new Date(certificate.created_at).toLocaleString()}
          </p>
        </div>

        {certificate.birth_rtmr3 && (
          <div>
            <p className="text-xs text-gray-500">Birth RTMR3 (Code Hash at Birth)</p>
            <p className="font-mono text-xs truncate" title={certificate.birth_rtmr3}>
              {certificate.birth_rtmr3.slice(0, 16)}...{certificate.birth_rtmr3.slice(-16)}
            </p>
          </div>
        )}

        <div>
          <p className="text-xs text-gray-500">Binding Digest</p>
          <p className="font-mono text-xs truncate" title={certificate.binding.digest}>
            {certificate.binding.digest.slice(0, 16)}...{certificate.binding.digest.slice(-16)}
          </p>
        </div>
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <a
          href="/attestation"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          View full birth certificate details
        </a>
      </div>
    </Card>
  );
}
