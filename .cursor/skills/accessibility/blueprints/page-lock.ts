// BLUEPRINT: Scroll/interaction lock for modal overlay stacking
// STRUCTURAL: setPageLock(locked, mainSelector?) — reference-counted; resetPageLock() — emergency escape
// ILLUSTRATIVE: mainSelector defaults to 'main'; adjust for non-standard layout roots;
//   the inert attribute hides content from assistive tech — ensure your target browser supports it
// SOURCE: app/frontend/src/lib/ui/utils/page-lock.ts

// Reference-counted so nested overlays (e.g. modal inside drawer) unwind correctly.
let lockCount = 0;

/**
 * Locks or unlocks page scroll and marks the main region as inert.
 * Uses a reference count so multiple callers can independently lock/unlock
 * without stepping on each other.
 */
export function setPageLock(locked: boolean, mainSelector = 'main'): void {
	if (typeof document === 'undefined') return;

	lockCount = Math.max(0, lockCount + (locked ? 1 : -1));
	const active = lockCount > 0;
	document.body.style.overflow = active ? 'hidden' : '';

	const main = document.querySelector(mainSelector);
	if (!(main instanceof HTMLElement)) return;

	main.toggleAttribute('inert', active);
}

/**
 * Hard-resets the lock count. Use only in teardown/cleanup — not as a substitute
 * for paired setPageLock(false) calls.
 */
export function resetPageLock(): void {
	lockCount = 0;
}
