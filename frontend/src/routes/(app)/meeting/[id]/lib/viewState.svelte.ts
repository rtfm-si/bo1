/**
 * View State - Tab selection and view mode management
 * Handles UI state for sub-problem tabs and contribution display modes
 */

import type { SSEEvent } from '$lib/api/sse-events';
import type { SubProblemTab } from './subProblemTabs';

export interface ViewStateConfig {
	getEventsBySubProblem: () => Map<number, SSEEvent[]>;
}

/**
 * Creates view state manager for UI display options
 */
export function createViewState(config: ViewStateConfig) {
	const { getEventsBySubProblem } = config;

	// ============================================================================
	// TAB STATE
	// ============================================================================

	let activeSubProblemTab = $state<string | undefined>(undefined);

	// ============================================================================
	// VIEW MODE STATE
	// ============================================================================

	let contributionViewMode = $state<'simple' | 'full'>('simple');
	let cardViewModes = $state<Map<string, 'simple' | 'full'>>(new Map());
	let showFullTranscripts = $state(false);

	// ============================================================================
	// DERIVED VALUES
	// ============================================================================

	const activeTabEvents = $derived.by(() => {
		if (!activeSubProblemTab) return [];
		const tabIndex = parseInt(activeSubProblemTab.replace('subproblem-', ''));
		const eventsBySubProblem = getEventsBySubProblem();
		return eventsBySubProblem.get(tabIndex) || [];
	});

	// ============================================================================
	// METHODS
	// ============================================================================

	function setActiveTab(tabId: string | undefined) {
		activeSubProblemTab = tabId;
	}

	function initializeTab(tabs: SubProblemTab[]) {
		if (tabs.length > 0 && !activeSubProblemTab) {
			activeSubProblemTab = tabs[0].id;
		}
	}

	function switchToConclusionIfCompleted(
		sessionStatus: string | undefined,
		showConclusionTab: boolean
	) {
		if (sessionStatus === 'completed' && showConclusionTab && activeSubProblemTab !== 'conclusion') {
			activeSubProblemTab = 'conclusion';
		}
	}

	function toggleCardViewMode(cardId: string) {
		const current = cardViewModes.get(cardId) ?? contributionViewMode;
		const next = current === 'simple' ? 'full' : 'simple';
		cardViewModes.set(cardId, next);
		cardViewModes = new Map(cardViewModes);
	}

	function setGlobalViewMode(mode: 'simple' | 'full') {
		contributionViewMode = mode;
		cardViewModes.clear();
		cardViewModes = new Map(cardViewModes);
	}

	function getCardViewMode(cardId: string): 'simple' | 'full' {
		return cardViewModes.get(cardId) ?? contributionViewMode;
	}

	function toggleFullTranscripts() {
		showFullTranscripts = !showFullTranscripts;
	}

	return {
		// Reactive getters
		get activeSubProblemTab() {
			return activeSubProblemTab;
		},
		get contributionViewMode() {
			return contributionViewMode;
		},
		get cardViewModes() {
			return cardViewModes;
		},
		get showFullTranscripts() {
			return showFullTranscripts;
		},
		get activeTabEvents() {
			return activeTabEvents;
		},

		// Methods
		setActiveTab,
		initializeTab,
		switchToConclusionIfCompleted,
		toggleCardViewMode,
		setGlobalViewMode,
		getCardViewMode,
		toggleFullTranscripts,
	};
}

export type ViewState = ReturnType<typeof createViewState>;
