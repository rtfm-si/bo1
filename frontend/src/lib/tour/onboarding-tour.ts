/**
 * Onboarding Tour Configuration
 *
 * Defines the driver.js tour steps for new user onboarding.
 * Steps guide users through:
 * 1. Business context setup
 * 2. First meeting creation
 * 3. Post-meeting views (Kanban & Gantt)
 * 4. Projects overview
 */

import { driver, type DriveStep, type Config, type Driver } from 'driver.js';
import 'driver.js/dist/driver.css';
import { apiClient } from '$lib/api/client';
import { skipTour, clearTourPage } from '$lib/stores/tour';

/**
 * Check if an element exists and is visible in the DOM
 */
export function isElementVisible(selector: string): boolean {
	const el = document.querySelector(selector);
	if (!el) return false;

	// Check if element or parent has display: none
	const style = window.getComputedStyle(el);
	if (style.display === 'none' || style.visibility === 'hidden') return false;

	// Check dimensions
	const rect = el.getBoundingClientRect();
	if (rect.width === 0 && rect.height === 0) return false;

	return true;
}

// Track navigation unsubscribe function
let unsubscribeNavigation: (() => void) | null = null;

// Reference to current tour driver instance
let currentTourDriver: Driver | null = null;

// Tour step IDs matching backend OnboardingStep enum
export type TourStepId = 'business_context' | 'first_meeting' | 'expert_panel' | 'results';

/**
 * Bo1 themed driver.js configuration
 */
const driverConfig: Config = {
	animate: true,
	showProgress: true,
	showButtons: ['next', 'previous', 'close'],
	allowClose: true, // Allow X button and overlay click to dismiss
	overlayColor: 'rgba(0, 0, 0, 0.7)',
	stagePadding: 8,
	stageRadius: 8,
	popoverClass: 'bo1-tour-popover',
	progressText: '{{current}} of {{total}}',
	nextBtnText: 'Next',
	prevBtnText: 'Back',
	doneBtnText: 'Done',
};

/** Callbacks for tour navigation actions */
export interface TourNavigationCallbacks {
	onNavigateToActions?: () => void;
	onNavigateToProjects?: () => void;
}

// Store navigation callbacks
let navigationCallbacks: TourNavigationCallbacks = {};

/**
 * Set navigation callbacks for tour
 */
export function setTourNavigationCallbacks(callbacks: TourNavigationCallbacks): void {
	navigationCallbacks = callbacks;
}

/**
 * Tour steps for the onboarding flow
 * Steps highlight key actions on the dashboard
 */
export function getOnboardingSteps(): DriveStep[] {
	return [
		{
			element: '[data-tour="new-meeting"]',
			popover: {
				title: 'Start Your First Meeting',
				description:
					'Describe a decision or challenge you\'re facing. Our panel of AI experts will deliberate and provide actionable recommendations.',
				side: 'bottom',
				align: 'start',
			},
		},
		{
			element: '[data-tour="actions-view"]',
			popover: {
				title: 'Track Your Actions',
				description:
					'After each meeting, actions are extracted and organized here. Use Kanban or Gantt views to manage progress.<br><br><strong>Want to explore?</strong> Click "Visit Actions" to see the Kanban board.',
				side: 'bottom',
				align: 'start',
				onPopoverRender: (popover) => {
					// Add custom button to visit Actions page
					const footer = popover.footerButtons;
					const visitBtn = document.createElement('button');
					visitBtn.innerText = 'Visit Actions →';
					visitBtn.className = 'driver-popover-btn bo1-visit-btn';
					visitBtn.onclick = () => {
						if (navigationCallbacks.onNavigateToActions) {
							navigationCallbacks.onNavigateToActions();
						} else {
							console.warn('Tour: onNavigateToActions callback not set');
						}
					};
					footer.appendChild(visitBtn);
				},
			},
		},
		{
			element: '[data-tour="context-nav"]',
			popover: {
				title: 'Set Up Your Business Context',
				description:
					'Click here to configure your business profile. Better context means more personalized expert advice.',
				side: 'bottom',
				align: 'center',
			},
		},
		{
			element: '[data-tour="projects-nav"]',
			popover: {
				title: 'Organize with Projects',
				description:
					'Group related meetings and actions into projects. Track progress across multiple decisions and initiatives.<br><br><strong>Want to explore?</strong> Click "Visit Projects" to see project management.',
				side: 'bottom',
				align: 'center',
				onPopoverRender: (popover) => {
					// Add custom button to visit Projects page
					const footer = popover.footerButtons;
					const visitBtn = document.createElement('button');
					visitBtn.innerText = 'Visit Projects →';
					visitBtn.className = 'driver-popover-btn bo1-visit-btn';
					visitBtn.onclick = () => {
						if (navigationCallbacks.onNavigateToProjects) {
							navigationCallbacks.onNavigateToProjects();
						} else {
							console.warn('Tour: onNavigateToProjects callback not set');
						}
					};
					footer.appendChild(visitBtn);
				},
			},
		},
		{
			element: '[data-tour="help-nav"]',
			popover: {
				title: 'Learn How It Connects',
				description:
					'Visit the Help Center to see an interactive diagram showing how Meetings, Actions, and Projects work together.',
				side: 'bottom',
				align: 'end',
			},
		},
	];
}

/**
 * Tour steps for the Actions page
 * Highlights Kanban board, view toggle, filters, and bulk actions
 */
export function getActionsPageSteps(): DriveStep[] {
	return [
		{
			element: '[data-tour="view-toggle"]',
			popover: {
				title: 'Switch Views',
				description:
					'Toggle between Kanban board for quick status updates and Gantt chart for timeline planning.',
				side: 'bottom',
				align: 'center',
			},
		},
		{
			element: '[data-tour="actions-filters"]',
			popover: {
				title: 'Filter Your Actions',
				description:
					'Filter by meeting, status, due date, project, or tags to focus on what matters most.',
				side: 'bottom',
				align: 'start',
			},
		},
		{
			element: '[data-tour="kanban-column"]',
			popover: {
				title: 'Drag and Drop',
				description:
					'Drag tasks between columns to update their status. Move from To Do → In Progress → Done as you complete work.',
				side: 'right',
				align: 'start',
			},
		},
	];
}

/**
 * Tour steps for the Projects page
 * Highlights project creation, idea generation, and project cards
 */
export function getProjectsPageSteps(): DriveStep[] {
	return [
		{
			element: '[data-tour="create-project"]',
			popover: {
				title: 'Create a Project',
				description:
					'Start a new project to group related meetings and actions together.',
				side: 'bottom',
				align: 'end',
			},
		},
		{
			element: '[data-tour="generate-ideas"]',
			popover: {
				title: 'Generate Project Ideas',
				description:
					'Let AI suggest projects based on your unassigned actions or business context.',
				side: 'bottom',
				align: 'end',
			},
		},
		{
			element: '[data-tour="project-card"]',
			popover: {
				title: 'Track Progress',
				description:
					'Each project card shows completion progress, action counts, and estimated dates. Click to view details.',
				side: 'top',
				align: 'start',
			},
		},
	];
}

/**
 * Filter steps to only include those with visible elements
 */
function getVisibleSteps(steps: DriveStep[]): DriveStep[] {
	return steps.filter((step) => {
		if (!step.element) return true; // Non-element steps always included
		return isElementVisible(step.element as string);
	});
}

/**
 * Cleanup tour resources (navigation lock, driver reference)
 */
export function cleanupTour(): void {
	if (unsubscribeNavigation) {
		unsubscribeNavigation();
		unsubscribeNavigation = null;
	}
	currentTourDriver = null;
}

/**
 * Destroy active tour driver and cleanup
 * Call this when navigating away to prevent popup persistence
 */
export function destroyActiveTour(): void {
	if (currentTourDriver) {
		currentTourDriver.destroy();
		currentTourDriver = null;
	}
	cleanupTour();
}

/**
 * Start the onboarding tour
 */
export async function startOnboardingTour(onComplete?: () => void): Promise<void> {
	// Get only steps with visible elements
	const steps = getVisibleSteps(getOnboardingSteps());

	// If no valid steps, skip tour entirely
	if (steps.length === 0) {
		console.warn('No visible tour elements found, skipping tour');
		onComplete?.();
		return;
	}

	const tourDriver = driver({
		...driverConfig,
		steps,
		onHighlightStarted: (element, step) => {
			// Validate element still exists before highlighting
			const selector = step.element as string | undefined;
			if (selector && !isElementVisible(selector)) {
				// Element not found - skip to next step
				console.warn(`Tour element not found: ${selector}, skipping step`);
				setTimeout(() => tourDriver.moveNext(), 100);
			}
		},
		onCloseClick: () => {
			// User clicked X button or overlay - skip tour
			cleanupTour();
			clearTourPage();
			skipTour();
			onComplete?.();
			tourDriver.destroy();
		},
		onDestroyStarted: async () => {
			// Cleanup navigation lock
			cleanupTour();

			// Mark tour as complete when user finishes (reaches end)
			try {
				await apiClient.completeTour();
			} catch (err) {
				console.error('Failed to mark tour complete:', err);
			}
			onComplete?.();
			tourDriver.destroy();
		},
		onNextClick: (element, step, opts) => {
			// Track step completion
			const stepIndex = opts.state.activeIndex ?? 0;
			const stepId = getStepIdByIndex(stepIndex);
			if (stepId) {
				apiClient.completeOnboardingStep(stepId).catch(console.error);
			}
			tourDriver.moveNext();
		},
	});

	// Store reference for external access
	currentTourDriver = tourDriver;

	tourDriver.drive();
}

/**
 * Start the Actions page tour
 */
export async function startActionsPageTour(onComplete?: () => void): Promise<void> {
	const steps = getVisibleSteps(getActionsPageSteps());

	if (steps.length === 0) {
		console.warn('No visible Actions page tour elements, skipping');
		onComplete?.();
		return;
	}

	const tourDriver = driver({
		...driverConfig,
		steps,
		onHighlightStarted: (element, step) => {
			const selector = step.element as string | undefined;
			if (selector && !isElementVisible(selector)) {
				console.warn(`Tour element not found: ${selector}, skipping step`);
				setTimeout(() => tourDriver.moveNext(), 100);
			}
		},
		onCloseClick: () => {
			cleanupTour();
			clearTourPage();
			skipTour();
			onComplete?.();
			tourDriver.destroy();
		},
		onDestroyStarted: () => {
			cleanupTour();
			clearTourPage();
			onComplete?.();
			tourDriver.destroy();
		},
	});

	currentTourDriver = tourDriver;
	tourDriver.drive();
}

/**
 * Start the Projects page tour
 */
export async function startProjectsPageTour(onComplete?: () => void): Promise<void> {
	const steps = getVisibleSteps(getProjectsPageSteps());

	if (steps.length === 0) {
		console.warn('No visible Projects page tour elements, skipping');
		onComplete?.();
		return;
	}

	const tourDriver = driver({
		...driverConfig,
		steps,
		onHighlightStarted: (element, step) => {
			const selector = step.element as string | undefined;
			if (selector && !isElementVisible(selector)) {
				console.warn(`Tour element not found: ${selector}, skipping step`);
				setTimeout(() => tourDriver.moveNext(), 100);
			}
		},
		onCloseClick: () => {
			cleanupTour();
			clearTourPage();
			skipTour();
			onComplete?.();
			tourDriver.destroy();
		},
		onDestroyStarted: () => {
			cleanupTour();
			clearTourPage();
			onComplete?.();
			tourDriver.destroy();
		},
	});

	currentTourDriver = tourDriver;
	tourDriver.drive();
}

/**
 * Map step index to step ID
 */
function getStepIdByIndex(index: number): TourStepId | null {
	const mapping: TourStepId[] = ['business_context', 'first_meeting', 'expert_panel', 'results'];
	return mapping[index] ?? null;
}

/**
 * Inject custom styles for the tour popover
 */
export function injectTourStyles(): void {
	const styleId = 'bo1-tour-styles';
	if (document.getElementById(styleId)) return;

	const style = document.createElement('style');
	style.id = styleId;
	style.textContent = `
		.bo1-tour-popover {
			--driver-theme: #00C8B3;
		}

		.driver-popover {
			background: white;
			border-radius: 12px;
			box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
			border: 1px solid #e3e8ea;
		}

		.driver-popover-title {
			font-size: 1rem;
			font-weight: 600;
			color: #1a2629;
		}

		.driver-popover-description {
			font-size: 0.875rem;
			color: #526b75;
			line-height: 1.5;
		}

		.driver-popover-progress-text {
			font-size: 0.75rem;
			color: #738891;
		}

		.driver-popover-prev-btn,
		.driver-popover-next-btn {
			padding: 0.5rem 1rem;
			border-radius: 6px;
			font-size: 0.875rem;
			font-weight: 500;
			transition: all 0.15s;
		}

		.driver-popover-prev-btn {
			background: #f1f4f5;
			color: #3f5459;
			border: 1px solid #d1d9dc;
		}

		.driver-popover-prev-btn:hover {
			background: #e3e8ea;
		}

		.driver-popover-next-btn {
			background: #00C8B3;
			color: white;
			border: none;
		}

		.driver-popover-next-btn:hover {
			background: #00a594;
		}

		.driver-popover-close-btn {
			color: #738891;
		}

		.driver-popover-close-btn:hover {
			color: #3f5459;
		}

		.driver-popover-arrow-side-left,
		.driver-popover-arrow-side-right,
		.driver-popover-arrow-side-top,
		.driver-popover-arrow-side-bottom {
			border-color: white !important;
		}

		/* Custom visit button styling */
		.bo1-visit-btn {
			background: transparent !important;
			color: #00C8B3 !important;
			border: 1px solid #00C8B3 !important;
			margin-left: 8px;
			padding: 0.5rem 1rem;
			border-radius: 6px;
			font-size: 0.875rem;
			font-weight: 500;
			cursor: pointer;
			transition: all 0.15s;
		}

		.bo1-visit-btn:hover {
			background: #00C8B3 !important;
			color: white !important;
		}

		/* Dark mode */
		@media (prefers-color-scheme: dark) {
			.driver-popover {
				background: #1e293b;
				border-color: #334155;
			}

			.driver-popover-title {
				color: #f1f5f9;
			}

			.driver-popover-description {
				color: #94a3b8;
			}

			.driver-popover-progress-text {
				color: #64748b;
			}

			.driver-popover-prev-btn {
				background: #334155;
				color: #e2e8f0;
				border-color: #475569;
			}

			.driver-popover-prev-btn:hover {
				background: #475569;
			}

			.driver-popover-arrow-side-left,
			.driver-popover-arrow-side-right,
			.driver-popover-arrow-side-top,
			.driver-popover-arrow-side-bottom {
				border-color: #1e293b !important;
			}

			.bo1-visit-btn {
				color: #00C8B3 !important;
				border-color: #00C8B3 !important;
			}

			.bo1-visit-btn:hover {
				background: #00C8B3 !important;
				color: #1e293b !important;
			}
		}
	`;

	document.head.appendChild(style);
}
