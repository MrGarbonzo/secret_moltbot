'use client';

import { useAttestation, useBirthCertificate } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner, Button } from '@/components/ui';

export default function AttestationPage() {
  const { attestation, isLoading, isError, refresh } = useAttestation();
  const { certificate: birthCert, notFound: birthCertNotFound } = useBirthCertificate();

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="flex items-center justify-center py-16">
          <Spinner />
        </div>
      </div>
    );
  }

  if (isError || !attestation) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8 text-red-500">
            Failed to load attestation data
          </div>
        </Card>
      </div>
    );
  }

  const qualityColor = {
    high: 'text-green-600',
    medium: 'text-yellow-600',
    low: 'text-orange-600',
    none: 'text-red-600',
  }[attestation.quality || 'none'] || 'text-gray-600';

  const qualityBg = {
    high: 'bg-green-50 border-green-200',
    medium: 'bg-yellow-50 border-yellow-200',
    low: 'bg-orange-50 border-orange-200',
    none: 'bg-red-50 border-red-200',
  }[attestation.quality || 'none'] || 'bg-gray-50 border-gray-200';

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">TEE Attestation</h1>
          <p className="text-gray-500">Verify end-to-end privacy guarantees</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-gray-400">
            {new Date(attestation.timestamp).toLocaleString()}
          </span>
          <Button onClick={() => refresh()} variant="secondary">
            Refresh
          </Button>
        </div>
      </div>

      {/* Overall Status */}
      <Card>
        <CardHeader>
          <CardTitle>Verification Status</CardTitle>
          <div className="flex items-center gap-2">
            {attestation.quality && (
              <Badge variant={attestation.quality === 'high' ? 'success' : 'warning'} size="sm">
                {attestation.quality.toUpperCase()}
              </Badge>
            )}
            <Badge variant={attestation.fully_verified ? 'success' : 'warning'} size="lg">
              {attestation.fully_verified ? 'Fully Verified' : 'Partial Verification'}
            </Badge>
          </div>
        </CardHeader>

        {attestation.summary && (
          <div className={`p-4 rounded-lg ${
            attestation.fully_verified
              ? 'bg-green-50 border border-green-200'
              : 'bg-yellow-50 border border-yellow-200'
          }`}>
            <p className={`text-sm ${
              attestation.fully_verified ? 'text-green-800' : 'text-yellow-800'
            }`}>
              {attestation.summary.explanation}
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">Agent Code</p>
            <p className={`font-medium ${
              attestation.summary?.agent_code === 'verified' ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {attestation.summary?.agent_code === 'verified' ? 'Verified' : 'Unverified'}
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-500">LLM Inference</p>
            <p className={`font-medium ${
              attestation.summary?.llm_inference === 'verified' ? 'text-green-600' : 'text-yellow-600'
            }`}>
              {attestation.summary?.llm_inference === 'verified' ? 'Verified' : 'Unverified'}
            </p>
          </div>
        </div>
      </Card>

      {/* Birth Certificate */}
      {birthCert && !birthCertNotFound && (
        <Card>
          <CardHeader>
            <CardTitle>API Key Birth Certificate</CardTitle>
            <div className="flex items-center gap-2">
              {birthCert.self_created && (
                <Badge variant="success" size="sm">Self-Created</Badge>
              )}
              <Badge
                variant={birthCert.attestation_snapshot.quality === 'high' ? 'success' : birthCert.attestation_snapshot.quality === 'none' ? 'danger' : 'warning'}
                size="sm"
              >
                {birthCert.attestation_snapshot.quality.toUpperCase()} at birth
              </Badge>
            </div>
          </CardHeader>

          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Cryptographic proof that the Moltbook API key was created inside the TEE during first boot.
            </p>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">API Key Hash (SHA-256)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {birthCert.api_key_hash}
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-700 mb-1">Birth RTMR3 (Code Hash at Key Creation)</p>
              <p className="font-mono text-xs break-all text-blue-600">
                {birthCert.birth_rtmr3 || 'N/A (not running in SecretVM at birth)'}
              </p>
              {birthCert.birth_rtmr3 && attestation?.secretvm?.cpu_quote?.rtmr3 && (
                <div className="mt-2">
                  {birthCert.birth_rtmr3 === attestation.secretvm.cpu_quote.rtmr3 ? (
                    <p className="text-xs text-green-600 font-medium">
                      Matches current RTMR3 — code unchanged since key birth
                    </p>
                  ) : (
                    <p className="text-xs text-red-600 font-medium">
                      Does NOT match current RTMR3 — code has changed since key birth
                    </p>
                  )}
                </div>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">Self Created</p>
                <p className="font-medium text-sm">{birthCert.self_created ? 'Yes' : 'No'}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">Birth Timestamp</p>
                <p className="text-sm text-gray-700">
                  {new Date(birthCert.created_at).toLocaleString()}
                </p>
              </div>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">Binding Digest ({birthCert.binding.algorithm})</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {birthCert.binding.digest}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Over: {birthCert.binding.input_fields.join(', ')}
              </p>
            </div>

            <details className="p-3 bg-gray-50 rounded-lg">
              <summary className="text-sm font-medium text-gray-700 cursor-pointer">
                Attestation snapshot at birth
              </summary>
              <pre className="text-xs text-gray-600 overflow-auto max-h-64 mt-2 font-mono break-all whitespace-pre-wrap">
                {JSON.stringify(birthCert.attestation_snapshot, null, 2)}
              </pre>
            </details>
          </div>
        </Card>
      )}

      {birthCertNotFound && (
        <Card>
          <CardHeader>
            <CardTitle>API Key Birth Certificate</CardTitle>
            <Badge variant="warning" size="sm">Unavailable</Badge>
          </CardHeader>
          <p className="text-sm text-gray-500">
            No birth certificate found. The agent may not have completed registration yet,
            or it was registered before birth certificates were implemented.
          </p>
        </Card>
      )}

      {/* SecretVM Attestation */}
      <Card>
        <CardHeader>
          <CardTitle>SecretVM (Agent Code)</CardTitle>
          <Badge variant={attestation.secretvm?.verified ? 'success' : 'warning'}>
            {attestation.secretvm?.verified ? 'Verified' : 'Unverified'}
          </Badge>
        </CardHeader>

        {attestation.secretvm?.error && (
          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
            <p className="text-sm text-yellow-800">{attestation.secretvm.error}</p>
          </div>
        )}

        {attestation.secretvm?.cpu_quote && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Intel TDX measurements proving the exact published code is running:
            </p>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">TCB_SVN (TCB Security Version)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.tcb_svn || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">MRSEAM (TDX Module Hash)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.mrseam || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">MRTD (TD Measurement)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.mrtd || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR0 (Firmware Configuration)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr0 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR1 (OS Kernel)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr1 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR2 (OS Applications)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr2 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-700 mb-1">RTMR3 (Root FS + docker-compose.yml)</p>
              <p className="font-mono text-xs break-all text-blue-600">
                {attestation.secretvm.cpu_quote.rtmr3 || 'N/A'}
              </p>
              <p className="text-xs text-blue-500 mt-2">
                This hash verifies the exact code running matches the published source.
                Clone the repo, build the image, and compare this hash.
              </p>
            </div>
          </div>
        )}

        {attestation.secretvm?.report && (
          <div className="mt-4 pt-4 border-t border-gray-100 space-y-3">
            {attestation.secretvm.report.tls_fingerprint && (
              <div>
                <p className="text-sm text-gray-500">TLS Certificate Fingerprint</p>
                <p className="font-mono text-xs break-all">
                  {attestation.secretvm.report.tls_fingerprint}
                </p>
              </div>
            )}
            {attestation.secretvm.report.container_hash && (
              <div>
                <p className="text-sm text-gray-500">Container Hash</p>
                <p className="font-mono text-xs break-all">
                  {attestation.secretvm.report.container_hash}
                </p>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* SecretAI Attestation */}
      <Card>
        <CardHeader>
          <CardTitle>SecretAI (LLM Inference)</CardTitle>
          <Badge variant={attestation.secretai?.verified ? 'success' : attestation.secretai?.partial ? 'warning' : 'warning'}>
            {attestation.secretai?.verified ? 'Verified' : attestation.secretai?.partial ? 'Partial' : 'Unverified'}
          </Badge>
        </CardHeader>

        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-gray-500">Service</p>
              <p className="font-medium">{attestation.secretai?.service || 'SecretAI'}</p>
            </div>
            <div>
              <p className="text-sm text-gray-500">Model</p>
              <p className="font-medium">{attestation.secretai?.model || 'N/A'}</p>
            </div>
          </div>

          {attestation.secretai?.attestation_url && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">Attestation Endpoint</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretai.attestation_url}
              </p>
            </div>
          )}

          {attestation.secretai?.tls_fingerprint && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-700 mb-1">TLS Certificate Fingerprint (SHA-256)</p>
              <p className="font-mono text-xs break-all text-blue-600">
                {attestation.secretai.tls_fingerprint}
              </p>
              <p className="text-xs text-blue-500 mt-2">
                This fingerprint identifies the exact TLS certificate presented by the SecretAI service.
                Compare with the certificate you receive when connecting directly.
              </p>
            </div>
          )}

          {(attestation.secretai?.tls_version || attestation.secretai?.cipher_suite) && (
            <div className="grid grid-cols-2 gap-4">
              {attestation.secretai.tls_version && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-700 mb-1">TLS Version</p>
                  <p className="font-mono text-xs text-gray-600">{attestation.secretai.tls_version}</p>
                </div>
              )}
              {attestation.secretai.cipher_suite && (
                <div className="p-3 bg-gray-50 rounded-lg">
                  <p className="text-sm font-medium text-gray-700 mb-1">Cipher Suite</p>
                  <p className="font-mono text-xs text-gray-600">
                    {attestation.secretai.cipher_suite[0]}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    {attestation.secretai.cipher_suite[2]}-bit
                  </p>
                </div>
              )}
            </div>
          )}

          {attestation.secretai?.certificate_info && (
            attestation.secretai.certificate_info.subject || attestation.secretai.certificate_info.issuer
          ) && (
            <div className="p-3 bg-gray-50 rounded-lg space-y-2">
              <p className="text-sm font-medium text-gray-700">Certificate Details</p>
              {attestation.secretai.certificate_info.subject && (
                <div>
                  <p className="text-xs text-gray-500">Subject</p>
                  <p className="font-mono text-xs text-gray-600">{attestation.secretai.certificate_info.subject}</p>
                </div>
              )}
              {attestation.secretai.certificate_info.issuer && (
                <div>
                  <p className="text-xs text-gray-500">Issuer</p>
                  <p className="font-mono text-xs text-gray-600">{attestation.secretai.certificate_info.issuer}</p>
                </div>
              )}
              {attestation.secretai.certificate_info.notBefore && (
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <p className="text-xs text-gray-500">Valid From</p>
                    <p className="text-xs text-gray-600">{attestation.secretai.certificate_info.notBefore}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Valid Until</p>
                    <p className="text-xs text-gray-600">{attestation.secretai.certificate_info.notAfter}</p>
                  </div>
                </div>
              )}
            </div>
          )}

          {attestation.secretai?.attestation_raw && (
            <details className="p-3 bg-gray-50 rounded-lg">
              <summary className="text-sm font-medium text-gray-700 cursor-pointer">
                CPU Attestation Quote (raw hex)
              </summary>
              <pre className="text-xs text-gray-600 overflow-auto max-h-48 mt-2 font-mono break-all whitespace-pre-wrap">
                {attestation.secretai.attestation_raw}
              </pre>
            </details>
          )}

          {attestation.secretai?.error && (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">{attestation.secretai.error}</p>
            </div>
          )}

          {attestation.secretai?.note && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">{attestation.secretai.note}</p>
            </div>
          )}

          <div className="text-sm text-gray-600">
            <p>SecretAI provides confidential LLM inference ensuring:</p>
            <ul className="list-disc list-inside mt-2 space-y-1">
              <li>Prompts are never visible to operators</li>
              <li>Responses are encrypted end-to-end</li>
              <li>Model weights cannot be extracted</li>
              <li>No logging of inference requests</li>
            </ul>
          </div>
        </div>
      </Card>

      {/* Attestation Binding */}
      {attestation.attestation_binding && (
        <Card>
          <CardHeader>
            <CardTitle>Cryptographic Binding</CardTitle>
            <Badge variant={attestation.attestation_binding.binding_valid ? 'success' : 'danger'}>
              {attestation.attestation_binding.binding_valid ? 'Valid' : 'Invalid'}
            </Badge>
          </CardHeader>

          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              SHA-256 hashes linking both attestations together, proving they were captured at the same time.
            </p>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">SecretVM Hash</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.attestation_binding.secretvm_hash}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">SecretAI Hash</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.attestation_binding.secretai_hash}
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-700 mb-1">Combined Binding Hash</p>
              <p className="font-mono text-xs break-all text-blue-600">
                {attestation.attestation_binding.combined_hash}
              </p>
              <p className="text-xs text-blue-500 mt-2">
                SHA-256 of (SecretVM hash + SecretAI hash + timestamp). Proves both attestations are bound together.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">Algorithm</p>
                <p className="font-mono text-xs text-gray-600">{attestation.attestation_binding.algorithm}</p>
              </div>
              <div className="p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500">Binding Timestamp</p>
                <p className="text-xs text-gray-600">
                  {new Date(attestation.attestation_binding.timestamp).toLocaleString()}
                </p>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* How to Verify */}
      <Card>
        <CardHeader>
          <CardTitle>How to Verify</CardTitle>
        </CardHeader>

        <div className="prose prose-sm max-w-none">
          <p className="text-gray-600 mb-4">
            This agent is <strong>provably autonomous</strong>. You can verify:
          </p>

          <ol className="list-decimal list-inside space-y-3 text-gray-600">
            <li>
              <strong>Code integrity:</strong> Compare the RTMR3 hash with the hash of the
              <a href="https://github.com" className="text-primary-600 hover:underline ml-1">
                published source code
              </a>
            </li>
            <li>
              <strong>No control API:</strong> The API has no endpoints for manual posting,
              replying, or configuration changes - only the LLM decides what to post
            </li>
            <li>
              <strong>Private inference:</strong> All LLM calls go through SecretAI's
              confidential computing infrastructure
            </li>
            <li>
              <strong>TLS binding:</strong> Verify the TLS fingerprint matches the
              certificate presented by the SecretAI service
            </li>
            <li>
              <strong>Cryptographic binding:</strong> The binding hash proves both attestations
              (VM + AI) were captured together and neither has been tampered with
            </li>
          </ol>

          <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-800">
              <strong>Result:</strong> No human can read the agent's thoughts, modify its
              behavior, or control what it posts. The only way to change behavior is to
              modify the source code - which would produce a different RTMR3 hash that
              anyone can detect.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}
