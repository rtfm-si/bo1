export interface SubProblemResult {
	id: string;
	goal: string;
	synthesis: string;
	status: 'complete' | 'in_progress' | 'failed' | 'pending';
}
