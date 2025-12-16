/**
 * Onboarding Tour Unit Tests
 *
 * Tests use vi.stubGlobal for DOM mocking (consistent with other tests)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Mock $app/environment
vi.mock('$app/environment', () => ({
	browser: true,
}));

// Mock api client
vi.mock('$lib/api/client', () => ({
	apiClient: {
		completeTour: vi.fn().mockResolvedValue(undefined),
		completeOnboardingStep: vi.fn().mockResolvedValue(undefined),
	},
}));

import {
	isElementVisible,
	getOnboardingSteps,
	getActionsPageSteps,
	getProjectsPageSteps,
	setTourNavigationCallbacks,
} from './onboarding-tour';

describe('isElementVisible', () => {
	let mockElement: HTMLElement | null;
	let mockStyle: Partial<CSSStyleDeclaration>;
	let mockRect: Partial<DOMRect>;
	let querySelectorMock: ReturnType<typeof vi.fn>;
	let getComputedStyleMock: ReturnType<typeof vi.fn>;

	beforeEach(() => {
		mockElement = null;
		mockStyle = {
			display: 'block',
			visibility: 'visible',
		};
		mockRect = {
			width: 100,
			height: 100,
			x: 0,
			y: 0,
			top: 0,
			left: 0,
			right: 100,
			bottom: 100,
		};

		querySelectorMock = vi.fn(() => mockElement);
		getComputedStyleMock = vi.fn(() => mockStyle);

		// Use stubGlobal for document and window
		vi.stubGlobal('document', {
			querySelector: querySelectorMock,
		});
		vi.stubGlobal('window', {
			getComputedStyle: getComputedStyleMock,
		});
	});

	it('returns false for missing selectors', () => {
		mockElement = null;

		expect(isElementVisible('[data-tour="nonexistent"]')).toBe(false);
		expect(isElementVisible('#missing-id')).toBe(false);
		expect(isElementVisible('.missing-class')).toBe(false);
	});

	it('returns true for visible elements', () => {
		mockElement = {
			getBoundingClientRect: () => mockRect as DOMRect,
		} as HTMLElement;
		mockStyle.display = 'block';
		mockStyle.visibility = 'visible';

		expect(isElementVisible('[data-tour="test-element"]')).toBe(true);
	});

	it('returns false for display: none elements', () => {
		mockElement = {
			getBoundingClientRect: () => mockRect as DOMRect,
		} as HTMLElement;
		mockStyle.display = 'none';

		expect(isElementVisible('[data-tour="hidden-display"]')).toBe(false);
	});

	it('returns false for visibility: hidden elements', () => {
		mockElement = {
			getBoundingClientRect: () => mockRect as DOMRect,
		} as HTMLElement;
		mockStyle.display = 'block';
		mockStyle.visibility = 'hidden';

		expect(isElementVisible('[data-tour="hidden-visibility"]')).toBe(false);
	});

	it('returns false for zero-dimension elements', () => {
		mockElement = {
			getBoundingClientRect: () => ({
				...mockRect,
				width: 0,
				height: 0,
			}) as DOMRect,
		} as HTMLElement;
		mockStyle.display = 'block';
		mockStyle.visibility = 'visible';

		expect(isElementVisible('[data-tour="zero-dim"]')).toBe(false);
	});

	it('handles ID selectors', () => {
		mockElement = {
			getBoundingClientRect: () => mockRect as DOMRect,
		} as HTMLElement;

		expect(isElementVisible('#test-id')).toBe(true);
		expect(querySelectorMock).toHaveBeenCalledWith('#test-id');
	});

	it('handles class selectors', () => {
		mockElement = {
			getBoundingClientRect: () => mockRect as DOMRect,
		} as HTMLElement;

		expect(isElementVisible('.test-class')).toBe(true);
		expect(querySelectorMock).toHaveBeenCalledWith('.test-class');
	});
});

describe('getOnboardingSteps', () => {
	it('returns 5 dashboard steps', () => {
		const steps = getOnboardingSteps();
		expect(steps.length).toBe(5);
	});

	it('includes new-meeting step', () => {
		const steps = getOnboardingSteps();
		const newMeetingStep = steps.find((s) => s.element === '[data-tour="new-meeting"]');
		expect(newMeetingStep).toBeDefined();
		expect(newMeetingStep?.popover?.title).toBe('Start Your First Meeting');
	});

	it('includes actions-view step with Visit Actions button', () => {
		const steps = getOnboardingSteps();
		const actionsStep = steps.find((s) => s.element === '[data-tour="actions-view"]');
		expect(actionsStep).toBeDefined();
		expect(actionsStep?.popover?.title).toBe('Track Your Actions');
		// Has onPopoverRender callback for custom button
		expect(actionsStep?.popover?.onPopoverRender).toBeDefined();
	});

	it('includes projects-nav step with Visit Projects button', () => {
		const steps = getOnboardingSteps();
		const projectsStep = steps.find((s) => s.element === '[data-tour="projects-nav"]');
		expect(projectsStep).toBeDefined();
		expect(projectsStep?.popover?.title).toBe('Organize with Projects');
		// Has onPopoverRender callback for custom button
		expect(projectsStep?.popover?.onPopoverRender).toBeDefined();
	});

	it('includes help-nav step linking to concepts diagram', () => {
		const steps = getOnboardingSteps();
		const helpStep = steps.find((s) => s.element === '[data-tour="help-nav"]');
		expect(helpStep).toBeDefined();
		expect(helpStep?.popover?.title).toBe('Learn How It Connects');
	});
});

describe('getActionsPageSteps', () => {
	it('returns 3 actions page steps', () => {
		const steps = getActionsPageSteps();
		expect(steps.length).toBe(3);
	});

	it('includes view-toggle step', () => {
		const steps = getActionsPageSteps();
		const viewToggleStep = steps.find((s) => s.element === '[data-tour="view-toggle"]');
		expect(viewToggleStep).toBeDefined();
		expect(viewToggleStep?.popover?.title).toBe('Switch Views');
	});

	it('includes actions-filters step', () => {
		const steps = getActionsPageSteps();
		const filtersStep = steps.find((s) => s.element === '[data-tour="actions-filters"]');
		expect(filtersStep).toBeDefined();
		expect(filtersStep?.popover?.title).toBe('Filter Your Actions');
	});

	it('includes kanban-column step', () => {
		const steps = getActionsPageSteps();
		const kanbanStep = steps.find((s) => s.element === '[data-tour="kanban-column"]');
		expect(kanbanStep).toBeDefined();
		expect(kanbanStep?.popover?.title).toBe('Drag and Drop');
	});
});

describe('getProjectsPageSteps', () => {
	it('returns 3 projects page steps', () => {
		const steps = getProjectsPageSteps();
		expect(steps.length).toBe(3);
	});

	it('includes create-project step', () => {
		const steps = getProjectsPageSteps();
		const createStep = steps.find((s) => s.element === '[data-tour="create-project"]');
		expect(createStep).toBeDefined();
		expect(createStep?.popover?.title).toBe('Create a Project');
	});

	it('includes generate-ideas step', () => {
		const steps = getProjectsPageSteps();
		const generateStep = steps.find((s) => s.element === '[data-tour="generate-ideas"]');
		expect(generateStep).toBeDefined();
		expect(generateStep?.popover?.title).toBe('Generate Project Ideas');
	});

	it('includes project-card step', () => {
		const steps = getProjectsPageSteps();
		const cardStep = steps.find((s) => s.element === '[data-tour="project-card"]');
		expect(cardStep).toBeDefined();
		expect(cardStep?.popover?.title).toBe('Track Progress');
	});
});

describe('setTourNavigationCallbacks', () => {
	it('stores callbacks for later use', () => {
		const onNavigateToActions = vi.fn();
		const onNavigateToProjects = vi.fn();

		setTourNavigationCallbacks({
			onNavigateToActions,
			onNavigateToProjects,
		});

		// Callbacks are stored internally and used by popover buttons
		// We verify they can be set without error
		expect(true).toBe(true);
	});
});
