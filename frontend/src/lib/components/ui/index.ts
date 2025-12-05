/**
 * Component Index - Barrel export for all UI components
 * Usage: import { Button, Card, Input } from '$lib/components/ui';
 */

// Existing components
export { default as Button } from './Button.svelte';
export { default as Card } from './Card.svelte';
export { default as Input } from './Input.svelte';
export { default as Badge } from './Badge.svelte';
export { default as Alert } from './Alert.svelte';

// New progressive disclosure components
export { default as ProgressBar } from './ProgressBar.svelte';
export { default as Spinner } from './Spinner.svelte';
export { default as Avatar } from './Avatar.svelte';
export { default as Tooltip } from './Tooltip.svelte';
export { default as Modal } from './Modal.svelte';
export { default as Dropdown } from './Dropdown.svelte';
export { default as Tabs } from './Tabs.svelte';
export { default as Toast } from './Toast.svelte';
export { default as InsightFlag } from './InsightFlag.svelte';
export { default as ContributionCard } from './ContributionCard.svelte';

// Phase 3: Polish & Enhancements
export { default as PhaseTimeline } from './PhaseTimeline.svelte';
export { default as RelativeTimestamp } from './RelativeTimestamp.svelte';
export { default as DualProgress } from './DualProgress.svelte';
export { default as DecisionMetrics } from './DecisionMetrics.svelte';
export { default as MeetingStatusBar } from './MeetingStatusBar.svelte';
export { default as SubProblemMetrics } from './SubProblemMetrics.svelte';
export { default as ConnectionStatus } from './ConnectionStatus.svelte';
export { default as SynthesisProgress } from './SynthesisProgress.svelte';

// Performance components
export { default as LazyRender } from './LazyRender.svelte';
export { default as VirtualizedList } from './VirtualizedList.svelte';

// Type exports for TypeScript consumers
export type { DropdownItem } from './Dropdown.svelte';
export type { Tab } from './Tabs.svelte';
export type { Persona } from './ContributionCard.svelte';
