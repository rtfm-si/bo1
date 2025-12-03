/**
 * Reactive intersection observer hook for Svelte 5.
 * Used for triggering animations when elements enter the viewport.
 */

import { onMount } from 'svelte';

export interface IntersectionObserverOptions {
	threshold?: number;
	rootMargin?: string;
	once?: boolean;
}

/**
 * Creates a reactive intersection observer that tracks when an element is visible.
 *
 * @param options - IntersectionObserver options plus 'once' to disconnect after first intersection
 * @returns Object with isIntersecting state and observe function
 *
 * @example
 * ```svelte
 * <script lang="ts">
 *   import { useIntersectionObserver } from '$lib/hooks/useIntersectionObserver.svelte';
 *
 *   const { isIntersecting, observe } = useIntersectionObserver({ threshold: 0.2 });
 * </script>
 *
 * <div use:observe class:visible={isIntersecting}>
 *   Content that animates when visible
 * </div>
 * ```
 */
export function useIntersectionObserver(options: IntersectionObserverOptions = {}) {
	const { threshold = 0.2, rootMargin = '0px', once = true } = options;

	let isIntersecting = $state(false);
	let observer: IntersectionObserver | null = null;
	let observedElement: Element | null = null;

	function observe(node: Element) {
		observedElement = node;

		if (typeof IntersectionObserver === 'undefined') {
			// Fallback for SSR or unsupported browsers
			isIntersecting = true;
			return { destroy() {} };
		}

		observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						isIntersecting = true;
						if (once && observer) {
							observer.disconnect();
						}
					} else if (!once) {
						isIntersecting = false;
					}
				});
			},
			{ threshold, rootMargin }
		);

		observer.observe(node);

		return {
			destroy() {
				observer?.disconnect();
			}
		};
	}

	return {
		get isIntersecting() {
			return isIntersecting;
		},
		observe
	};
}

/**
 * Creates multiple intersection observers for tracking visibility of multiple sections.
 * Useful for staggered animations on landing pages.
 *
 * @param sectionIds - Array of section IDs to observe
 * @param options - IntersectionObserver options
 * @returns Map of section IDs to visibility states
 *
 * @example
 * ```svelte
 * <script lang="ts">
 *   import { useSectionObservers } from '$lib/hooks/useIntersectionObserver.svelte';
 *
 *   const visibility = useSectionObservers(['hero', 'features', 'pricing']);
 * </script>
 *
 * <section id="hero" class:visible={visibility.get('hero')}>...</section>
 * ```
 */
export function useSectionObservers(
	sectionIds: string[],
	options: IntersectionObserverOptions = {}
) {
	const { threshold = 0.2, rootMargin = '0px' } = options;

	const visibility = $state(new Map<string, boolean>(sectionIds.map((id) => [id, false])));

	onMount(() => {
		const observers = new Map<string, IntersectionObserver>();

		sectionIds.forEach((id) => {
			const observer = new IntersectionObserver(
				(entries) => {
					entries.forEach((entry) => {
						if (entry.isIntersecting) {
							visibility.set(id, true);
							observer.disconnect();
						}
					});
				},
				{ threshold, rootMargin }
			);

			const element = document.getElementById(id);
			if (element) {
				observer.observe(element);
				observers.set(id, observer);
			}
		});

		return () => {
			observers.forEach((observer) => observer.disconnect());
		};
	});

	return visibility;
}
