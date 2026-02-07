// TypeScript interfaces matching API schemas

export interface Agent {
  id: string;
  name: string;
  description: string;
  karma: number;
  created_at: string;
}

export interface Post {
  id: string;
  submolt: string;
  author: string;
  title: string;
  content?: string;
  url?: string;
  score: number;
  comment_count: number;
  created_at: string;
  seen?: boolean;
}

export interface Comment {
  id: string;
  post_id: string;
  author: string;
  content: string;
  score: number;
  parent_id?: string;
  created_at: string;
}

export interface Activity {
  id: string;
  type: 'post' | 'comment' | 'upvote' | 'downvote';
  timestamp: string;
  data: Record<string, unknown>;
}

export interface AgentStats {
  total_posts: number;
  total_comments: number;
  total_votes: number;
  seen_posts: number;
}

export type AgentState = 'booting' | 'registering' | 'registered' | 'verified' | 'error';

export interface StatusResponse {
  // Always present
  state: AgentState;
  agent_name: string;
  model: string;
  online: boolean;

  // Present when state == "registered" (onboarding)
  claim_url?: string;
  verification_code?: string;
  message?: string;

  // Present when state == "error"
  error?: string;

  // Present when state == "verified" (normal operation)
  paused?: boolean;
  karma?: number;
  stats?: AgentStats;
  last_heartbeat?: string;
  next_heartbeat?: string;
}

export interface VerificationResponse {
  verified: boolean;
  message: string;
}

export interface ActivityResponse {
  activities: Activity[];
}

export interface FeedResponse {
  posts: Post[];
}

export interface MemoryResponse {
  seen_count: number;
  activity_stats: Record<string, number>;
  personality_notes: string[];
  recent_activity: Activity[];
}

export interface ConfigResponse {
  state: string;
  heartbeat_interval_hours: number;
  paused: boolean;
  agent_name: string;
  agent_description: string;
  subscribed_submolts: string[];
}

export interface HeartbeatResult {
  status: string;
  posts_created: number;
  comments_created: number;
  votes_cast: number;
  errors: string[];
}

export interface GeneratedContent {
  title: string;
  content: string;
}

export interface CpuQuote {
  mrtd: string;
  mrseam: string;
  rtmr0: string;
  rtmr1: string;
  rtmr2: string;
  rtmr3: string;
  tcb_svn: string;
  raw_quote?: string;
}

export interface AttestationReport {
  tls_fingerprint: string;
  container_hash: string;
  timestamp: string;
}

export interface SecretVMAttestation {
  cpu_quote: CpuQuote | null;
  report: AttestationReport | null;
  tee_type: string;
  verified: boolean;
  error?: string;
  timestamp: string;
}

export interface SecretAIAttestation {
  source?: string;
  service: string;
  model: string;
  attestation_url?: string;
  attestation_raw?: string;
  tls_fingerprint?: string;
  tls_version?: string;
  cipher_suite?: [string, string, number];
  certificate_info?: {
    subject: string | null;
    issuer: string | null;
    notBefore: string | null;
    notAfter: string | null;
  };
  verified: boolean;
  partial?: boolean;
  error?: string;
  note?: string;
  hint?: string;
  timestamp: string;
}

export interface AttestationSummary {
  agent_code: 'verified' | 'unverified';
  llm_inference: 'verified' | 'unverified';
  end_to_end_privacy: 'guaranteed' | 'partial';
  explanation: string;
}

export interface AttestationBinding {
  version: string;
  algorithm: string;
  secretvm_hash: string;
  secretai_hash: string;
  combined_hash: string;
  timestamp: string;
  binding_valid: boolean;
}

export interface AttestationData {
  secretvm: SecretVMAttestation | null;
  secretai: SecretAIAttestation | null;
  attestation_binding?: AttestationBinding;
  fully_verified: boolean;
  quality?: string;
  summary?: AttestationSummary;
  error?: string;
  timestamp: string;
}

export interface BirthCertificateBinding {
  algorithm: string;
  input_fields: string[];
  digest: string;
}

export interface BirthCertificate {
  version: string;
  created_at: string;
  agent_name: string;
  agent_description: string;
  api_key_hash: string;
  birth_rtmr3: string | null;
  self_created: boolean;
  attestation_snapshot: {
    secretvm: SecretVMAttestation | null;
    secretai: SecretAIAttestation | null;
    fully_verified: boolean;
    quality: string;
  };
  binding: BirthCertificateBinding;
}
