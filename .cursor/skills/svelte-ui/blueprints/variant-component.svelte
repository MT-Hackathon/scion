<!-- BLUEPRINT: variant-component
     STRUCTURAL: variant union type, size union type, $props() with rest spread,
                 Record<Variant,string> lookup maps per dimension, $derived class
                 composition, accessible focus ring, disabled + loading guard, snippet children
     ILLUSTRATIVE: variant/size names, specific token names, loading indicator choice,
                   base element (plain button shown; swap for bits-ui Root or anchor as needed) -->

<script lang="ts">
	import type { Snippet } from 'svelte';

	// STRUCTURAL: named union types — never bare string — so Record maps are exhaustive
	type Variant = 'primary' | 'secondary' | 'outline'; // ILLUSTRATIVE: your variant names
	type Size = 'sm' | 'md' | 'lg';                     // ILLUSTRATIVE: your size names

	let {
		variant = 'primary',
		size = 'md',
		disabled = false,
		loading = false,
		class: className = '',
		children,
		...restProps
	}: {
		variant?: Variant;
		size?: Size;
		disabled?: boolean;
		loading?: boolean;
		class?: string;
		children?: Snippet;
		[key: string]: unknown;
	} = $props();

	// STRUCTURAL: one Record lookup map per style dimension keeps template free of conditionals
	const variantClasses: Record<Variant, string> = {
		primary:   'bg-[var(--button-primary-bg)] text-[var(--button-primary-text)] hover:bg-[var(--button-primary-hover-bg)]',   // ILLUSTRATIVE
		secondary: 'bg-[var(--button-secondary-bg)] text-[var(--button-secondary-text)] border border-[var(--button-secondary-border)]', // ILLUSTRATIVE
		outline:   'bg-transparent border border-[var(--button-outline-border)] text-[var(--button-outline-text)]',                      // ILLUSTRATIVE
	};

	const sizeClasses: Record<Size, string> = {
		sm: 'h-8 px-3 text-sm rounded-md gap-1.5',   // ILLUSTRATIVE
		md: 'h-10 px-4 text-sm rounded-md gap-2',    // ILLUSTRATIVE
		lg: 'h-12 px-6 text-base rounded-lg gap-2',  // ILLUSTRATIVE
	};

	// STRUCTURAL: $derived assembles final class string once — never concatenate in markup
	const classes = $derived(
		[
			'inline-flex items-center justify-center font-medium transition-colors',
			// STRUCTURAL: focus ring uses a single semantic token, not a hardcoded color
			'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--interactive-focus)] focus-visible:ring-offset-2',
			'disabled:opacity-50 disabled:pointer-events-none',
			variantClasses[variant],
			sizeClasses[size],
			className,
		].join(' ')
	);
</script>

<!-- STRUCTURAL: disabled || loading both prevent interaction; aria-busy signals async state to AT; rest props forward all native attrs -->
<button class={classes} disabled={disabled || loading} aria-busy={loading} {...restProps}>
	{#if loading}
		<!-- ILLUSTRATIVE: replace with your branded loading indicator (e.g. GraftMark pulse) -->
		<span
			class="size-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent"
			aria-hidden="true"
		/>
	{/if}
	{@render children?.()}
</button>
