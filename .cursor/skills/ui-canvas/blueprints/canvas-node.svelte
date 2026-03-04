<!-- BLUEPRINT: canvas-node
     STRUCTURAL: NodeProps binding, Snippet children, handle placement, token-based styling, selected state, Svelte 5 rune syntax
     ILLUSTRATIVE: node type name ('source' | 'transformation' | 'destination'), label field, body content (replace with your domain) -->

<script lang="ts">
	import type { Snippet } from 'svelte';
	import { Handle, Position } from '@xyflow/svelte';
	import type { NodeProps } from '@xyflow/svelte';

	// STRUCTURAL: intersection adds Snippet children to SvelteFlow's NodeProps type
	let { data, selected, children }: NodeProps<{ label: string }> & { children?: Snippet } = $props();
</script>

<!-- STRUCTURAL: outer wrapper carries token-based styling and selected state -->
<div
	class="node"
	class:selected
>
	<!-- STRUCTURAL: accent bar anchors visual identity to node type via token -->
	<div class="node-header">
		<!-- ILLUSTRATIVE: replace 'label' with your node's primary display field -->
		<span class="node-label">{data.label}</span>
	</div>

	<div class="node-body">
		<!-- ILLUSTRATIVE: node-specific content (config summary, status indicators) -->
		{@render children?.()}
	</div>

	<!-- STRUCTURAL: handle placement contracts — match exactly to node type role
	     Source-only:    type="source" Position.Right, no target handle
	     Target-only:    type="target" Position.Left,  no source handle
	     Transform:      both handles present -->
	<Handle type="target" position={Position.Left} />
	<Handle type="source" position={Position.Right} />
</div>

<style>
	/* STRUCTURAL: color and shadow values come from the --node-* token system; never hardcode */
	.node {
		/* ILLUSTRATIVE: replace 'source' suffix with your type: 'transformation' or 'destination' */
		background: var(--node-gradient-source);
		border: 2px solid var(--node-border-source);
		box-shadow: var(--node-shadow-source);
		border-radius: 8px; /* ILLUSTRATIVE */
		min-width: 160px;   /* ILLUSTRATIVE */
		transition: box-shadow 0.15s ease, border-color 0.15s ease;
	}

	/* STRUCTURAL: selected state uses -active token variant — never override with raw values */
	.node.selected {
		border-color: var(--node-border-source-active);
		box-shadow: var(--node-shadow-source-strong);
	}

	/* STRUCTURAL: accent bar left-border ties visual type identity to the color token */
	.node-header {
		/* ILLUSTRATIVE: replace 'source' with your type */
		border-left: 4px solid var(--node-color-source); /* ILLUSTRATIVE: border width */
		padding: 8px 12px; /* ILLUSTRATIVE */
		border-radius: 6px 6px 0 0; /* ILLUSTRATIVE: match node border-radius minus border width */
	}

	.node-label {
		font-size: 0.875rem; /* ILLUSTRATIVE */
		font-weight: 600;    /* ILLUSTRATIVE */
	}

	.node-body {
		padding: 8px 12px; /* ILLUSTRATIVE */
	}
</style>
