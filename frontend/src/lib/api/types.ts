/**
 * API Types - TypeScript interfaces for Board of One API
 *
 * These types match the Pydantic models in backend/api/models.py
 */

export interface CreateSessionRequest {
	problem_statement: string;
	problem_context?: Record<string, unknown>;
}

export interface SessionResponse {
	id: string;
	status: 'active' | 'paused' | 'completed' | 'failed' | 'killed' | 'deleted' | 'created';
	phase: string | null;
	created_at: string;
	updated_at: string;
	last_activity_at?: string;
	problem_statement: string;
	cost?: number | null;
	// Summary counts for dashboard cards
	expert_count?: number | null;
	contribution_count?: number | null;
	task_count?: number | null;
	focus_area_count?: number | null;
}

export interface SessionDetailResponse extends SessionResponse {
	problem?: {
		statement: string;
		context?: Record<string, unknown>;
		sub_problems?: Array<{
			id: string;
			goal: string;
		}>;
	};
	state?: {
		synthesis?: string;
		final_synthesis?: string;
		recommendations?: Array<{
			persona_code: string;
			recommendation: string;
			reasoning: string;
			confidence: number;
			conditions?: string[];
		}>;
		round_number?: number;
		max_rounds?: number;
		duration_seconds?: number;
		[key: string]: any;
	};
	metrics?: {
		total_cost: number;
		total_tokens: number;
		phase_costs: Record<string, number>;
		convergence_score?: number;
		duration_seconds?: number;
	};
	contributions?: Array<{
		persona_code: string;
		content: string;
		round_number: number;
		timestamp: string;
	}>;
	round_number?: number;
	max_rounds?: number;
}

export interface SessionListResponse {
	sessions: SessionResponse[];
	total: number;
	limit: number;
	offset: number;
}

export interface ControlResponse {
	status: string;
	message?: string;
}

export interface HealthResponse {
	status: 'healthy' | 'unhealthy';
	details?: Record<string, unknown>;
}

export interface ApiError {
	detail: string;
	status?: number;
}

export interface UserContext {
	business_model?: string;
	target_market?: string;
	product_description?: string;
	revenue?: string;
	customers?: string;
	growth_rate?: string;
	competitors?: string;
	website?: string;
}

export interface UserContextResponse {
	exists: boolean;
	context?: UserContext;
	updated_at?: string;
}

// ============================================================================
// Admin Types
// ============================================================================

/**
 * Admin user information with metrics
 */
export interface AdminUser {
	user_id: string;
	email: string;
	auth_provider: string;
	subscription_tier: string;
	is_admin: boolean;
	is_locked: boolean;
	locked_at: string | null;
	lock_reason: string | null;
	deleted_at: string | null;
	total_meetings: number;
	total_cost: number | null;
	last_meeting_at: string | null;
	last_meeting_id: string | null;
	created_at: string;
	updated_at: string;
}

/**
 * Admin user list response
 */
export interface AdminUserListResponse {
	total_count: number;
	users: AdminUser[];
	page: number;
	per_page: number;
}

/**
 * Admin user update request
 */
export interface AdminUserUpdateRequest {
	subscription_tier?: string;
	is_admin?: boolean;
}

/**
 * Beta whitelist entry
 */
export interface WhitelistEntry {
	id: string;
	email: string;
	added_by: string | null;
	notes: string | null;
	created_at: string;
}

/**
 * Beta whitelist response
 */
export interface WhitelistResponse {
	total_count: number;
	emails: WhitelistEntry[];
	env_emails: string[];
}

/**
 * Waitlist entry
 */
export interface WaitlistEntry {
	id: string;
	email: string;
	status: string;
	source: string | null;
	notes: string | null;
	created_at: string;
}

/**
 * Waitlist response
 */
export interface WaitlistResponse {
	total_count: number;
	pending_count: number;
	entries: WaitlistEntry[];
}

/**
 * Waitlist approval response
 */
export interface WaitlistApprovalResponse {
	email: string;
	whitelist_added: boolean;
	email_sent: boolean;
	message: string;
}

/**
 * Extracted task from synthesis
 */
export interface ExtractedTask {
	id: string;
	description: string;
	category: string;
	priority: string;
	suggested_completion_date: string | null;
	dependencies: string[];
	source_section: string;
	confidence: number;
}

/**
 * Task extraction response
 */
export interface TaskExtractionResponse {
	tasks: ExtractedTask[];
	total_tasks: number;
	extraction_confidence: number;
	synthesis_sections_analyzed: string[];
}

/**
 * Session events response
 */
export interface SessionEventsResponse {
	session_id: string;
	events: unknown[];
	count: number;
}
