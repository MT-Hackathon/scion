// BLUEPRINT: Linear arrow-key navigation and focus-by-index for list/grid components
// STRUCTURAL: nextLinearIndex(key, index, length) → number | null; focusRowByIndex(index, root?) → boolean
// ILLUSTRATIVE: data-row-index attribute name is a convention — change to match your DOM structure;
//   nextLinearIndex only handles up/down; extend the pattern for left/right or Home/End
// SOURCE: app/frontend/src/lib/ui/utils/keyboard-nav.ts

/**
 * Returns the next focus index for ArrowUp/ArrowDown within a bounded list.
 * Returns null when the key is not handled or the boundary is already reached.
 */
export function nextLinearIndex(key: string, index: number, length: number): number | null {
	if (length <= 0) return null;
	if (key === 'ArrowDown' && index < length - 1) return index + 1;
	if (key === 'ArrowUp' && index > 0) return index - 1;
	return null;
}

/**
 * Focuses the element with [data-row-index="<index>"] inside `root`.
 * Falls back to document when root is not provided.
 * Returns false when no matching element is found.
 */
export function focusRowByIndex(index: number, root?: ParentNode | null): boolean {
	const resolvedRoot = root ?? (typeof document !== 'undefined' ? document : null);
	if (!resolvedRoot) return false;

	const el = resolvedRoot.querySelector<HTMLElement>(`[data-row-index="${index}"]`);
	if (!el) return false;

	el.focus();
	return true;
}
