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
