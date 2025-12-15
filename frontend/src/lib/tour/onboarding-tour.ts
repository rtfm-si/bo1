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

import { driver, type DriveStep, type Config } from 'driver.js';
import 'driver.js/dist/driver.css';
import { goto } from '$app/navigation';
import { apiClient } from '$lib/api/client';

// Tour step IDs matching backend OnboardingStep enum
export type TourStepId = 'business_context' | 'first_meeting' | 'expert_panel' | 'results';

/**
 * Bo1 themed driver.js configuration
 */
const driverConfig: Config = {
	animate: true,
	showProgress: true,
	showButtons: ['next', 'previous', 'close'],
	allowClose: true,
	overlayColor: 'rgba(0, 0, 0, 0.7)',
	stagePadding: 8,
	stageRadius: 8,
	popoverClass: 'bo1-tour-popover',
	progressText: '{{current}} of {{total}}',
	nextBtnText: 'Next',
	prevBtnText: 'Back',
	doneBtnText: 'Done',
};

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
					'After each meeting, actions are extracted and organized here. Use Kanban or Gantt views to manage progress.',
				side: 'bottom',
				align: 'start',
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
					'Group related meetings and actions into projects. Track progress across multiple decisions and initiatives.',
				side: 'bottom',
				align: 'center',
			},
		},
	];
}

/**
 * Start the onboarding tour
 */
export async function startOnboardingTour(onComplete?: () => void): Promise<void> {
	const steps = getOnboardingSteps();

	const tourDriver = driver({
		...driverConfig,
		steps,
		onDestroyStarted: async () => {
			// Mark tour as complete when user finishes or closes
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
		}
	`;

	document.head.appendChild(style);
}
