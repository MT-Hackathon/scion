// BLUEPRINT: Focus trap for modal/overlay keyboard containment
// STRUCTURAL: FOCUSABLE_SELECTOR constant; trapTabFocus(event, container) → boolean signature
// ILLUSTRATIVE: selector list is a starting point — extend for custom focusable elements;
//   call trapTabFocus in the modal's keydown handler and return early when it returns true
// SOURCE: app/frontend/src/lib/ui/utils/focus-trap.ts

export const FOCUSABLE_SELECTOR =
	'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Wraps Tab/Shift+Tab focus within `container`.
 * Returns true when the event was intercepted (caller should not propagate further).
 */
export function trapTabFocus(event: KeyboardEvent, container: ParentNode): boolean {
	if (event.key !== 'Tab') return false;

	const nodes = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
	if (nodes.length === 0) return false;

	const first = nodes[0];
	const last = nodes[nodes.length - 1];
	const wrapBack = event.shiftKey && document.activeElement === first;
	const wrapForward = !event.shiftKey && document.activeElement === last;
	if (!wrapBack && !wrapForward) return false;

	event.preventDefault();
	if (wrapBack) {
		last.focus();
		return true;
	}

	first.focus();
	return true;
}
