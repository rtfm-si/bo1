/**
 * Event Components - Barrel Export
 * Svelte 5 components for rendering SSE deliberation events
 *
 * NOTE: For optimal performance, meeting/[id]/+page.svelte uses dynamic imports
 * to load components on-demand, reducing initial bundle size by 30-40%.
 * These static exports are kept for backwards compatibility with other imports.
 *
 * If adding new event components, update the componentLoaders map in
 * meeting/[id]/+page.svelte for dynamic loading.
 */

export { default as DecompositionComplete } from './DecompositionComplete.svelte';
export { default as PersonaSelection } from './PersonaSelection.svelte';
export { default as FacilitatorDecision } from './FacilitatorDecision.svelte';
export { default as ModeratorIntervention } from './ModeratorIntervention.svelte';
export { default as ConvergenceCheck } from './ConvergenceCheck.svelte';
export { default as RecommendationPhase } from './RecommendationPhase.svelte';
export { default as PersonaRecommendation } from './PersonaRecommendation.svelte';
export { default as SynthesisComplete } from './SynthesisComplete.svelte';
export { default as SubProblemProgress } from './SubProblemProgress.svelte';
export { default as PhaseTable } from './PhaseTable.svelte';
export { default as DeliberationComplete } from './DeliberationComplete.svelte';
export { default as ErrorEvent } from './ErrorEvent.svelte';
export { default as GenericEvent } from './GenericEvent.svelte';
export { default as ActionableTasks } from './ActionableTasks.svelte';
export { default as ExpertPerspectiveCard } from './ExpertPerspectiveCard.svelte';
export { default as RecommendationResults } from './RecommendationResults.svelte';
export { default as ExpertPanel } from './ExpertPanel.svelte';
export { default as ActionPlan } from './ActionPlan.svelte';
