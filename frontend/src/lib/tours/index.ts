/**
 * Driver.js tour configurations for onboarding.
 *
 * Provides guided tours for:
 * - New user onboarding (business context setup)
 * - First meeting walkthrough
 * - Feature discovery
 */

import { driver, type DriveStep, type Config } from 'driver.js';
import 'driver.js/dist/driver.css';
import { trackEvent, AnalyticsEvents, trackTourStep } from '$lib/utils/analytics';

/**
 * Tour step identifiers matching backend OnboardingStep enum.
 */
export const TourSteps = {
	BUSINESS_CONTEXT: 'business_context',
	FIRST_MEETING: 'first_meeting',
	EXPERT_PANEL: 'expert_panel',
	RESULTS: 'results'
} as const;

/**
 * Common driver configuration.
 */
const baseConfig: Partial<Config> = {
	animate: true,
	showProgress: true,
	showButtons: ['next', 'previous', 'close'],
	nextBtnText: 'Next',
	prevBtnText: 'Back',
	doneBtnText: 'Done',
	popoverClass: 'bo1-tour-popover',
	stagePadding: 10,
	stageRadius: 8
};

/**
 * Onboarding tour steps - shown after login for new users.
 */
export const onboardingSteps: DriveStep[] = [
	{
		element: '#onboarding-welcome',
		popover: {
			title: 'Welcome to Board of One!',
			description:
				"Let's set up your business context so our AI experts can provide tailored strategic advice.",
			side: 'bottom',
			align: 'center'
		}
	},
	{
		element: '#company-name-input',
		popover: {
			title: 'Company Name',
			description: 'Enter your company name to personalize your experience.',
			side: 'bottom',
			align: 'start'
		}
	},
	{
		element: '#website-url-input',
		popover: {
			title: 'Website URL (Optional)',
			description:
				"Add your website URL and we'll automatically extract business information to save you time.",
			side: 'bottom',
			align: 'start'
		}
	},
	{
		element: '#business-stage-select',
		popover: {
			title: 'Business Stage',
			description:
				'Select your current stage to help our experts understand your context.',
			side: 'bottom',
			align: 'start'
		}
	},
	{
		element: '#primary-objective-select',
		popover: {
			title: 'Primary Objective',
			description: "What's your main focus right now? This helps prioritize advice.",
			side: 'bottom',
			align: 'start'
		}
	}
];

/**
 * Dashboard tour steps - quick intro to the main interface.
 */
export const dashboardSteps: DriveStep[] = [
	{
		element: '#start-meeting-button',
		popover: {
			title: 'Start a Meeting',
			description:
				'Click here to create a new strategic meeting with AI experts.',
			side: 'bottom',
			align: 'center'
		}
	},
	{
		element: '#recent-meetings',
		popover: {
			title: 'Recent Meetings',
			description: 'View your past meetings and their recommendations here.',
			side: 'top',
			align: 'center'
		}
	},
	{
		element: '#user-menu',
		popover: {
			title: 'Settings & Profile',
			description:
				'Access your business context settings and account options here.',
			side: 'left',
			align: 'start'
		}
	}
];

/**
 * Meeting tour steps - shown during first meeting.
 */
export const meetingSteps: DriveStep[] = [
	{
		element: '#problem-statement',
		popover: {
			title: 'Your Decision',
			description: "This is the decision you're seeking advice on.",
			side: 'bottom',
			align: 'center'
		}
	},
	{
		element: '#expert-panel',
		popover: {
			title: 'Your Expert Panel',
			description:
				'These AI experts will analyze your decision from different perspectives.',
			side: 'left',
			align: 'start'
		}
	},
	{
		element: '#contributions-feed',
		popover: {
			title: 'Expert Contributions',
			description:
				'Watch as experts discuss and debate the best approach to your decision.',
			side: 'right',
			align: 'start'
		}
	},
	{
		element: '#meeting-progress',
		popover: {
			title: 'Meeting Progress',
			description: 'Track the deliberation progress and key metrics here.',
			side: 'left',
			align: 'center'
		}
	}
];

/**
 * Results tour steps - shown when viewing first meeting results.
 */
export const resultsSteps: DriveStep[] = [
	{
		element: '#synthesis-section',
		popover: {
			title: 'Strategic Synthesis',
			description:
				'A comprehensive summary of the expert discussion and key insights.',
			side: 'bottom',
			align: 'center'
		}
	},
	{
		element: '#recommendations-section',
		popover: {
			title: 'Recommendations',
			description: 'Actionable recommendations from the expert panel.',
			side: 'bottom',
			align: 'center'
		}
	},
	{
		element: '#actions-section',
		popover: {
			title: 'Action Items',
			description:
				'Track your action items in a Kanban board to stay organized.',
			side: 'top',
			align: 'center'
		}
	}
];

/**
 * Create and start a tour with the given steps.
 *
 * @param steps - Tour steps to show
 * @param onComplete - Callback when tour completes
 * @param onDismiss - Callback when tour is dismissed
 */
export function startTour(
	steps: DriveStep[],
	onComplete?: () => void,
	onDismiss?: () => void
): ReturnType<typeof driver> {
	const tourDriver = driver({
		...baseConfig,
		steps,
		onDestroyStarted: () => {
			// Track tour completion or dismissal
			if (tourDriver.isLastStep()) {
				trackEvent(AnalyticsEvents.TOUR_COMPLETED);
				onComplete?.();
			} else {
				trackEvent(AnalyticsEvents.TOUR_DISMISSED);
				onDismiss?.();
			}
			tourDriver.destroy();
		},
		onNextClick: () => {
			const currentStep = tourDriver.getActiveIndex();
			if (currentStep !== undefined) {
				trackTourStep(`step_${currentStep + 1}`);
			}
			tourDriver.moveNext();
		}
	});

	trackEvent(AnalyticsEvents.TOUR_STARTED);
	tourDriver.drive();

	return tourDriver;
}

/**
 * Start the onboarding tour.
 */
export function startOnboardingTour(
	onComplete?: () => void,
	onDismiss?: () => void
): ReturnType<typeof driver> {
	return startTour(onboardingSteps, onComplete, onDismiss);
}

/**
 * Start the dashboard tour.
 */
export function startDashboardTour(
	onComplete?: () => void,
	onDismiss?: () => void
): ReturnType<typeof driver> {
	return startTour(dashboardSteps, onComplete, onDismiss);
}

/**
 * Start the meeting tour.
 */
export function startMeetingTour(
	onComplete?: () => void,
	onDismiss?: () => void
): ReturnType<typeof driver> {
	return startTour(meetingSteps, onComplete, onDismiss);
}

/**
 * Start the results tour.
 */
export function startResultsTour(
	onComplete?: () => void,
	onDismiss?: () => void
): ReturnType<typeof driver> {
	return startTour(resultsSteps, onComplete, onDismiss);
}

/**
 * Highlight a specific element without a full tour.
 *
 * @param selector - CSS selector for the element
 * @param title - Popover title
 * @param description - Popover description
 */
export function highlightElement(
	selector: string,
	title: string,
	description: string
): ReturnType<typeof driver> {
	const highlightDriver = driver({
		...baseConfig,
		showProgress: false,
		steps: [
			{
				element: selector,
				popover: {
					title,
					description,
					side: 'bottom',
					align: 'center'
				}
			}
		]
	});

	highlightDriver.drive();
	return highlightDriver;
}
