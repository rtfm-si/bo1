/**
 * API helpers for E2E test setup/teardown.
 *
 * Use direct API calls to set up test data instead of going through UI.
 * This makes tests faster and more reliable.
 */
import type { APIRequestContext } from '@playwright/test';

const API_BASE_URL = process.env.E2E_API_URL || 'http://localhost:8000';

export interface Session {
	id: string;
	problem_statement: string;
	status: string;
}

export interface Action {
	id: string;
	title: string;
	status: string;
	meeting_id: string;
}

export interface Dataset {
	id: string;
	name: string;
	source: string;
}

/**
 * API client for test data setup.
 */
export class TestApiClient {
	constructor(private request: APIRequestContext) {}

	/**
	 * Create a new meeting session.
	 */
	async createSession(problemStatement: string): Promise<Session> {
		const response = await this.request.post(`${API_BASE_URL}/api/v1/sessions`, {
			data: { problem_statement: problemStatement }
		});

		if (!response.ok()) {
			throw new Error(`Failed to create session: ${response.status()} ${await response.text()}`);
		}

		return response.json();
	}

	/**
	 * Get session by ID.
	 */
	async getSession(sessionId: string): Promise<Session> {
		const response = await this.request.get(`${API_BASE_URL}/api/v1/sessions/${sessionId}`);

		if (!response.ok()) {
			throw new Error(`Failed to get session: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * List user's sessions.
	 */
	async listSessions(): Promise<Session[]> {
		const response = await this.request.get(`${API_BASE_URL}/api/v1/sessions`);

		if (!response.ok()) {
			throw new Error(`Failed to list sessions: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * Delete a session.
	 */
	async deleteSession(sessionId: string): Promise<void> {
		const response = await this.request.delete(`${API_BASE_URL}/api/v1/sessions/${sessionId}`);

		if (!response.ok() && response.status() !== 404) {
			throw new Error(`Failed to delete session: ${response.status()}`);
		}
	}

	/**
	 * Create an action for a meeting.
	 */
	async createAction(
		meetingId: string,
		title: string,
		options?: { description?: string; due_date?: string; priority?: string }
	): Promise<Action> {
		const response = await this.request.post(`${API_BASE_URL}/api/v1/actions`, {
			data: {
				meeting_id: meetingId,
				title,
				...options
			}
		});

		if (!response.ok()) {
			throw new Error(`Failed to create action: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * List actions.
	 */
	async listActions(filters?: { status?: string; meeting_id?: string }): Promise<Action[]> {
		const params = new URLSearchParams();
		if (filters?.status) params.set('status', filters.status);
		if (filters?.meeting_id) params.set('meeting_id', filters.meeting_id);

		const response = await this.request.get(`${API_BASE_URL}/api/v1/actions?${params}`);

		if (!response.ok()) {
			throw new Error(`Failed to list actions: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * Update action status.
	 */
	async updateActionStatus(actionId: string, status: string): Promise<Action> {
		const response = await this.request.patch(`${API_BASE_URL}/api/v1/actions/${actionId}`, {
			data: { status }
		});

		if (!response.ok()) {
			throw new Error(`Failed to update action: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * Delete an action.
	 */
	async deleteAction(actionId: string): Promise<void> {
		const response = await this.request.delete(`${API_BASE_URL}/api/v1/actions/${actionId}`);

		if (!response.ok() && response.status() !== 404) {
			throw new Error(`Failed to delete action: ${response.status()}`);
		}
	}

	/**
	 * Upload a CSV dataset.
	 */
	async uploadDataset(name: string, csvContent: string): Promise<Dataset> {
		const formData = new FormData();
		formData.append('file', new Blob([csvContent], { type: 'text/csv' }), `${name}.csv`);

		const response = await this.request.post(`${API_BASE_URL}/api/v1/datasets/upload`, {
			multipart: {
				file: {
					name: `${name}.csv`,
					mimeType: 'text/csv',
					buffer: Buffer.from(csvContent)
				}
			}
		});

		if (!response.ok()) {
			throw new Error(`Failed to upload dataset: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * List datasets.
	 */
	async listDatasets(): Promise<Dataset[]> {
		const response = await this.request.get(`${API_BASE_URL}/api/v1/datasets`);

		if (!response.ok()) {
			throw new Error(`Failed to list datasets: ${response.status()}`);
		}

		return response.json();
	}

	/**
	 * Delete a dataset.
	 */
	async deleteDataset(datasetId: string): Promise<void> {
		const response = await this.request.delete(`${API_BASE_URL}/api/v1/datasets/${datasetId}`);

		if (!response.ok() && response.status() !== 404) {
			throw new Error(`Failed to delete dataset: ${response.status()}`);
		}
	}

	/**
	 * Clean up all test data for the current user.
	 * Call this in test teardown.
	 */
	async cleanupTestData(): Promise<void> {
		// Delete all sessions
		const sessions = await this.listSessions();
		for (const session of sessions) {
			await this.deleteSession(session.id);
		}

		// Delete all actions
		const actions = await this.listActions();
		for (const action of actions) {
			await this.deleteAction(action.id);
		}

		// Delete all datasets
		const datasets = await this.listDatasets();
		for (const dataset of datasets) {
			await this.deleteDataset(dataset.id);
		}
	}
}
