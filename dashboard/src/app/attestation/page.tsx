'use client';

import { useAttestation } from '@/lib/hooks';
import { Card, CardHeader, CardTitle, Badge, Spinner, Button } from '@/components/ui';

export default function AttestationPage() {
  const { attestation, isLoading, isError, refresh } = useAttestation();

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

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">TEE Attestation</h1>
          <p className="text-gray-500">Verify end-to-end privacy guarantees</p>
        </div>
        <Button onClick={() => refresh()} variant="secondary">
          Refresh
        </Button>
      </div>

      {/* Overall Status */}
      <Card>
        <CardHeader>
          <CardTitle>Verification Status</CardTitle>
          <Badge variant={attestation.fully_verified ? 'success' : 'warning'} size="lg">
            {attestation.fully_verified ? 'Fully Verified' : 'Partial Verification'}
          </Badge>
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
              <p className="text-sm font-medium text-gray-700 mb-1">MRTD (Firmware Hash)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.mrtd || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR0 (Configuration)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr0 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR1 (Linux Kernel)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr1 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">RTMR2 (Application)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.rtmr2 || 'N/A'}
              </p>
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm font-medium text-blue-700 mb-1">RTMR3 (Root FS + Docker)</p>
              <p className="font-mono text-xs break-all text-blue-600">
                {attestation.secretvm.cpu_quote.rtmr3 || 'N/A'}
              </p>
              <p className="text-xs text-blue-500 mt-2">
                This hash verifies the exact code running matches the published source.
              </p>
            </div>

            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-1">Report Data (TLS Fingerprint)</p>
              <p className="font-mono text-xs break-all text-gray-600">
                {attestation.secretvm.cpu_quote.reportdata || 'N/A'}
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
          <Badge variant={attestation.secretai?.verified ? 'success' : 'warning'}>
            {attestation.secretai?.verified ? 'Verified' : 'Unverified'}
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

          {attestation.secretai?.attestation && (
            <div className="p-3 bg-gray-50 rounded-lg">
              <p className="text-sm font-medium text-gray-700 mb-2">Attestation Data</p>
              <pre className="text-xs text-gray-600 overflow-auto max-h-48">
                {JSON.stringify(attestation.secretai.attestation, null, 2)}
              </pre>
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
              certificate presented by this server
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
