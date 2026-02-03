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

export interface StatusResponse {
  online: boolean;
  paused: boolean;
  karma: number;
  stats: AgentStats;
  last_heartbeat?: string;
  next_heartbeat?: string;
  model: string;
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
  heartbeat_interval_hours: number;
  paused: boolean;
  agent_name: string;
  active_submolts: string[];
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
  rtmr0: string;
  rtmr1: string;
  rtmr2: string;
  rtmr3: string;
  reportdata: string;
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
  attestation: Record<string, unknown> | null;
  service: string;
  model: string;
  verified: boolean;
  error?: string;
  note?: string;
  timestamp: string;
}

export interface AttestationSummary {
  agent_code: 'verified' | 'unverified';
  llm_inference: 'verified' | 'unverified';
  end_to_end_privacy: 'guaranteed' | 'partial';
  explanation: string;
}

export interface AttestationData {
  secretvm: SecretVMAttestation | null;
  secretai: SecretAIAttestation | null;
  fully_verified: boolean;
  summary?: AttestationSummary;
  error?: string;
  timestamp: string;
}
