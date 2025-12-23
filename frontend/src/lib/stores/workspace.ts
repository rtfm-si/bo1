/**
 * Workspace store - manages current workspace state and persistence.
 *
 * Uses Svelte 5 compatible store pattern that works with both:
 * - Svelte 5 runes ($derived, etc.)
 * - Svelte 4 auto-subscription ($store syntax)
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';
import { apiClient } from '$lib/api/client';
import type { WorkspaceResponse } from '$lib/api/types';
import { createLogger } from '$lib/utils/debug';

const log = createLogger('Workspace');
const STORAGE_KEY = 'bo1_current_workspace_id';

export interface WorkspaceState {
	workspaces: WorkspaceResponse[];
	currentWorkspace: WorkspaceResponse | null;
	defaultWorkspaceId: string | null;
	isLoading: boolean;
	error: string | null;
}

const initialState: WorkspaceState = {
	workspaces: [],
	currentWorkspace: null,
	defaultWorkspaceId: null,
	isLoading: false,
	error: null,
};

// Create writable store
const workspaceStore = writable<WorkspaceState>(initialState);

// Derived stores for convenience
// Sort workspaces to put default workspace first
export const workspaces = derived(workspaceStore, ($ws) => {
	if (!$ws.defaultWorkspaceId) return $ws.workspaces;
	return [...$ws.workspaces].sort((a, b) => {
		if (a.id === $ws.defaultWorkspaceId) return -1;
		if (b.id === $ws.defaultWorkspaceId) return 1;
		return 0;
	});
});
export const currentWorkspace = derived(workspaceStore, ($ws) => $ws.currentWorkspace);
export const defaultWorkspaceId = derived(workspaceStore, ($ws) => $ws.defaultWorkspaceId);
export const isWorkspaceLoading = derived(workspaceStore, ($ws) => $ws.isLoading);
export const workspaceError = derived(workspaceStore, ($ws) => $ws.error);

/**
 * Get persisted workspace ID from localStorage
 */
function getPersistedWorkspaceId(): string | null {
	if (!browser) return null;
	try {
		return localStorage.getItem(STORAGE_KEY);
	} catch {
		return null;
	}
}

/**
 * Persist workspace ID to localStorage
 */
function persistWorkspaceId(workspaceId: string | null): void {
	if (!browser) return;
	try {
		if (workspaceId) {
			localStorage.setItem(STORAGE_KEY, workspaceId);
		} else {
			localStorage.removeItem(STORAGE_KEY);
		}
	} catch (e) {
		log.warn('Failed to persist workspace ID:', e);
	}
}

/**
 * Load workspaces for the current user.
 * Auto-selects the persisted workspace or first workspace if none persisted.
 */
export async function loadWorkspaces(): Promise<void> {
	if (!browser) return;

	log.log('Loading workspaces...');

	workspaceStore.update((state) => ({ ...state, isLoading: true, error: null }));

	try {
		const response = await apiClient.listWorkspaces();
		const workspaceList = response.workspaces;
		const defaultWorkspaceId = response.default_workspace_id;

		log.log(`Loaded ${workspaceList.length} workspaces`);

		// Try to restore persisted workspace
		const persistedId = getPersistedWorkspaceId();
		let selected: WorkspaceResponse | null = null;

		if (persistedId) {
			selected = workspaceList.find((w) => w.id === persistedId) || null;
			if (!selected) {
				log.log('Persisted workspace not found, clearing');
				persistWorkspaceId(null);
			}
		}

		// Fall back to user's default workspace if no persisted selection
		if (!selected && defaultWorkspaceId) {
			selected = workspaceList.find((w) => w.id === defaultWorkspaceId) || null;
			if (selected) {
				persistWorkspaceId(selected.id);
				log.log(`Selected user default workspace: ${selected.name}`);
			}
		}

		// Auto-select first workspace if still none selected
		if (!selected && workspaceList.length > 0) {
			selected = workspaceList[0];
			persistWorkspaceId(selected.id);
			log.log(`Auto-selected first workspace: ${selected.name}`);
		}

		workspaceStore.set({
			workspaces: workspaceList,
			currentWorkspace: selected,
			defaultWorkspaceId: defaultWorkspaceId ?? null,
			isLoading: false,
			error: null,
		});
	} catch (e) {
		log.warn('Failed to load workspaces:', e);
		workspaceStore.update((state) => ({
			...state,
			isLoading: false,
			error: e instanceof Error ? e.message : 'Failed to load workspaces',
		}));
	}
}

/**
 * Switch to a different workspace
 */
export function switchWorkspace(workspaceId: string): void {
	workspaceStore.update((state) => {
		const workspace = state.workspaces.find((w) => w.id === workspaceId);
		if (workspace) {
			log.log(`Switching to workspace: ${workspace.name}`);
			persistWorkspaceId(workspaceId);
			return { ...state, currentWorkspace: workspace };
		}
		return state;
	});
}

/**
 * Create a new workspace and switch to it
 */
export async function createWorkspace(name: string, slug?: string): Promise<WorkspaceResponse | null> {
	log.log(`Creating workspace: ${name}`);

	workspaceStore.update((state) => ({ ...state, isLoading: true, error: null }));

	try {
		const newWorkspace = await apiClient.createWorkspace(name, slug);
		log.log(`Created workspace: ${newWorkspace.name} (${newWorkspace.id})`);

		workspaceStore.update((state) => ({
			...state,
			workspaces: [...state.workspaces, newWorkspace],
			currentWorkspace: newWorkspace,
			isLoading: false,
			error: null,
		}));

		persistWorkspaceId(newWorkspace.id);
		return newWorkspace;
	} catch (e) {
		log.warn('Failed to create workspace:', e);
		workspaceStore.update((state) => ({
			...state,
			isLoading: false,
			error: e instanceof Error ? e.message : 'Failed to create workspace',
		}));
		return null;
	}
}

/**
 * Clear workspace state (on sign out)
 */
export function clearWorkspaceState(): void {
	log.log('Clearing workspace state');
	persistWorkspaceId(null);
	workspaceStore.set(initialState);
}

/**
 * Refresh workspace list (e.g., after accepting an invitation)
 */
export async function refreshWorkspaces(): Promise<void> {
	await loadWorkspaces();
}

// Export store
export default workspaceStore;
