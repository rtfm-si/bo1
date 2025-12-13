/**
 * PDF Report Generator Unit Tests
 *
 * Tests action rendering in PDF reports including:
 * - Full action details (description, what_and_how, success_criteria)
 * - Truncation of long descriptions
 * - Overdue highlighting
 * - Empty state handling
 *
 * To run: npm run test
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { generateReportHTML, type ReportAction } from './pdf-report-generator';
import type { SSEEvent } from '$lib/api/sse-events';

// Mock session data
const mockSession = {
	id: 'test-session-123',
	problem: {
		statement: 'Should we expand to new market?',
		context: {}
	},
	status: 'completed',
	phase: 'synthesis',
	created_at: '2024-01-15T10:00:00Z'
};

// Mock events
const mockEvents: SSEEvent[] = [
	{
		type: 'expert_selected',
		data: {
			persona: {
				name: 'Strategic Analyst',
				displayName: 'Strategic Analyst',
				archetype: 'Business Strategist',
				expertise: ['Strategy', 'Growth']
			}
		},
		timestamp: '2024-01-15T10:01:00Z',
		sequence: 1
	} as any
];

// Mock actions
const createMockAction = (overrides: Partial<ReportAction> = {}): ReportAction => ({
	id: 'action-1',
	title: 'Research competitor pricing',
	description: 'Analyze competitor pricing strategies in target market.',
	status: 'todo',
	priority: 'high',
	timeline: '1 week',
	target_end_date: '2024-02-01',
	what_and_how: ['Research online sources', 'Contact industry experts'],
	success_criteria: ['Pricing data for 5+ competitors', 'Comparison spreadsheet complete'],
	dependencies: ['Market research complete'],
	category: 'research',
	...overrides
});

describe('pdf-report-generator', () => {
	describe('generateReportHTML - action details', () => {
		it('renders action title and description', () => {
			const actions = [createMockAction()];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Research competitor pricing');
			expect(html).toContain('Analyze competitor pricing strategies');
		});

		it('renders status and priority badges', () => {
			const actions = [createMockAction({ status: 'in_progress', priority: 'medium' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('status-in-progress');
			expect(html).toContain('priority-medium');
		});

		it('renders what_and_how section', () => {
			const actions = [createMockAction()];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('How to Complete');
			expect(html).toContain('Research online sources');
			expect(html).toContain('Contact industry experts');
		});

		it('renders success_criteria section', () => {
			const actions = [createMockAction()];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Success Criteria');
			expect(html).toContain('Pricing data for 5+ competitors');
		});

		it('renders dependencies section', () => {
			const actions = [createMockAction()];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Dependencies');
			expect(html).toContain('Market research complete');
		});

		it('renders category badge', () => {
			const actions = [createMockAction({ category: 'implementation' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('action-category');
			expect(html).toContain('implementation');
		});

		it('renders due date', () => {
			const actions = [createMockAction({ target_end_date: '2024-02-15' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Due:');
			expect(html).toContain('15 Feb 2024');
		});
	});

	describe('generateReportHTML - truncation', () => {
		it('truncates long descriptions', () => {
			const longDescription = 'A'.repeat(600);
			const actions = [createMockAction({ description: longDescription })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			// Description should be truncated at ~500 chars
			expect(html).not.toContain('A'.repeat(600));
			expect(html).toContain('...');
		});

		it('truncates list items beyond limit', () => {
			const manyItems = Array(10).fill('Step item for testing');
			const actions = [createMockAction({ what_and_how: manyItems })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			// Should show "+X more..." for items beyond limit
			expect(html).toContain('+7 more...');
		});

		it('limits to 50 actions maximum', () => {
			const manyActions = Array(60)
				.fill(null)
				.map((_, i) => createMockAction({ id: `action-${i}`, title: `Action ${i}` }));

			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions: manyActions
			});

			// Should show truncation notice
			expect(html).toContain('+10 more actions not shown');
			// Should show count in header
			expect(html).toContain('Action Items (60)');
		});
	});

	describe('generateReportHTML - overdue highlighting', () => {
		it('highlights overdue actions', () => {
			// Use a past date that's definitely overdue
			const pastDate = '2020-01-01';
			const actions = [createMockAction({ target_end_date: pastDate, status: 'todo' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('action-overdue');
			expect(html).toContain('(Overdue)');
		});

		it('does not highlight completed actions as overdue', () => {
			const pastDate = '2020-01-01';
			const actions = [createMockAction({ target_end_date: pastDate, status: 'done' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).not.toContain('action-overdue');
			expect(html).not.toContain('(Overdue)');
		});

		it('does not highlight cancelled actions as overdue', () => {
			const pastDate = '2020-01-01';
			const actions = [createMockAction({ target_end_date: pastDate, status: 'cancelled' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).not.toContain('action-overdue');
		});
	});

	describe('generateReportHTML - empty state', () => {
		it('renders empty state message when no actions', () => {
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions: []
			});

			expect(html).toContain('No actions were generated for this meeting');
			expect(html).toContain('actions-empty');
		});

		it('handles undefined actions gracefully', () => {
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions: undefined
			});

			// Should still generate valid HTML without crashing
			expect(html).toContain('<!DOCTYPE html>');
		});
	});

	describe('generateReportHTML - progress fields', () => {
		it('renders progress percentage', () => {
			const actions = [
				createMockAction({ progress_value: 75, progress_type: 'percentage' })
			];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Progress: 75%');
		});

		it('renders progress points', () => {
			const actions = [createMockAction({ progress_value: 5, progress_type: 'points' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Progress: 5 pts');
		});

		it('renders effort estimate', () => {
			const actions = [createMockAction({ estimated_effort_points: 8 })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Effort: 8 pts');
		});

		it('renders assignee', () => {
			const actions = [createMockAction({ assignee: 'John Doe' })];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			expect(html).toContain('Assigned: John Doe');
		});
	});

	describe('generateReportHTML - sorting', () => {
		it('sorts actions by priority (high first)', () => {
			const actions = [
				createMockAction({ id: '1', title: 'Low priority', priority: 'low' }),
				createMockAction({ id: '2', title: 'High priority', priority: 'high' }),
				createMockAction({ id: '3', title: 'Medium priority', priority: 'medium' })
			];
			const html = generateReportHTML({
				session: mockSession,
				events: mockEvents,
				sessionId: mockSession.id,
				actions
			});

			const highIndex = html.indexOf('High priority');
			const mediumIndex = html.indexOf('Medium priority');
			const lowIndex = html.indexOf('Low priority');

			expect(highIndex).toBeLessThan(mediumIndex);
			expect(mediumIndex).toBeLessThan(lowIndex);
		});
	});
});
