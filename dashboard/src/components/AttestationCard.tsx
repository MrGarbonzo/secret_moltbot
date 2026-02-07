'use client';

import { useAttestation } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner } from '@/components/ui';

export function AttestationCard() {
  const { attestation, isLoading, isError } = useAttestation();

  if (isLoading) {
    return (
      <Card>
        <div className="flex items-center justify-center py-8">
          <Spinner />
        </div>
      </Card>
    );
  }

  if (isError || !attestation) {
    return (
      <Card>
        <div className="text-center py-8 text-red-500">
          Failed to load attestation data
        </div>
      </Card>
    );
  }

  const qualityLabel = {
    high: 'High',
    medium: 'Medium',
    low: 'Low',
    none: 'None',
  }[attestation.quality || 'none'] || 'Unknown';

  return (
    <Card>
      <CardHeader>
        <CardTitle>TEE Attestation</CardTitle>
        <div className="flex items-center gap-2">
          {attestation.quality && (
            <Badge variant={attestation.quality === 'high' ? 'success' : 'warning'} size="sm">
              {qualityLabel}
            </Badge>
          )}
          <Badge variant={attestation.fully_verified ? 'success' : 'warning'}>
            {attestation.fully_verified ? 'Fully Verified' : 'Partial'}
          </Badge>
        </div>
      </CardHeader>

      <div className="space-y-4">
        {/* SecretVM Status */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">Agent Code (SecretVM)</p>
            <p className="text-xs text-gray-500">Intel TDX TEE</p>
          </div>
          <Badge variant={attestation.secretvm?.verified ? 'success' : 'warning'} size="sm">
            {attestation.secretvm?.verified ? 'Verified' : 'Unverified'}
          </Badge>
        </div>

        {/* SecretAI Status */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium">LLM Inference (SecretAI)</p>
            <p className="text-xs text-gray-500">{attestation.secretai?.model || 'N/A'}</p>
          </div>
          <Badge variant={attestation.secretai?.verified ? 'success' : 'warning'} size="sm">
            {attestation.secretai?.verified ? 'Verified' : attestation.secretai?.partial ? 'Partial' : 'Unverified'}
          </Badge>
        </div>

        {/* Code Hash (RTMR3) — show when VM is verified */}
        {attestation.secretvm?.cpu_quote?.rtmr3 && (
          <div>
            <p className="text-xs text-gray-500">Code Hash (RTMR3)</p>
            <p className="font-mono text-xs truncate" title={attestation.secretvm.cpu_quote.rtmr3}>
              {attestation.secretvm.cpu_quote.rtmr3.slice(0, 16)}...{attestation.secretvm.cpu_quote.rtmr3.slice(-16)}
            </p>
          </div>
        )}

        {/* TLS Fingerprint — show when SecretAI is verified (especially when VM is not) */}
        {attestation.secretai?.tls_fingerprint && (
          <div>
            <p className="text-xs text-gray-500">SecretAI TLS Fingerprint</p>
            <p className="font-mono text-xs truncate" title={attestation.secretai.tls_fingerprint}>
              {attestation.secretai.tls_fingerprint.slice(0, 16)}...{attestation.secretai.tls_fingerprint.slice(-16)}
            </p>
          </div>
        )}

        {/* Binding Status */}
        {attestation.attestation_binding && (
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">Cryptographic Binding</p>
            <Badge variant={attestation.attestation_binding.binding_valid ? 'success' : 'danger'} size="sm">
              {attestation.attestation_binding.binding_valid ? 'Valid' : 'Invalid'}
            </Badge>
          </div>
        )}

        {/* Summary */}
        {attestation.summary && (
          <div className={`text-xs p-2 rounded ${
            attestation.fully_verified
              ? 'bg-green-50 text-green-700'
              : attestation.secretai?.verified
                ? 'bg-blue-50 text-blue-700'
                : 'bg-yellow-50 text-yellow-700'
          }`}>
            {attestation.summary.end_to_end_privacy === 'guaranteed'
              ? 'End-to-end privacy guaranteed'
              : attestation.secretai?.verified
                ? 'LLM inference verified — VM attestation requires SecretVM'
                : 'Partial verification - see details'}
          </div>
        )}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-100">
        <a
          href="/attestation"
          className="text-sm text-primary-600 hover:text-primary-700"
        >
          View full attestation details
        </a>
      </div>
    </Card>
  );
}
