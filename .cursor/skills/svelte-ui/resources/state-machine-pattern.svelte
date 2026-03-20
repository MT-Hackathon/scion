<!--
  Canonical Rootstock state machine pattern for multi-step pages.

  USE THIS when a page has mutually exclusive phases (not just show/hide flags).
  The vault page at storage/vault/+page.svelte is the canonical implementation.

  KEY PRINCIPLE: States are mutually exclusive. Each phase defines the COMPLETE set of
  visible UI — not "what's different from the previous state." When phase changes, the
  old UI disappears entirely and the new UI appears. Never layer phases on top of each other.

  See also: interaction-design skill, Section 1 (State Machine Contracts).
-->

<script lang="ts">
  // 1. Define phases as a discriminated union — the single source of truth.
  //    Phase-specific data lives on the phase object, not as separate top-level state.
  type Phase =
    | { kind: 'idle' }
    | { kind: 'loading' }
    | { kind: 'form'; draft: string }
    | { kind: 'submitting'; draft: string }
    | { kind: 'success'; result: string }
    | { kind: 'error'; message: string };

  // 2. Single reactive state variable for the current phase.
  let phase = $state<Phase>({ kind: 'idle' });

  // 3. Transition functions — each defines a valid phase transition.
  //    Name them after the action, not the destination state.
  function openForm() {
    phase = { kind: 'form', draft: '' };
  }

  function cancelForm() {
    phase = { kind: 'idle' };
  }

  async function submit() {
    if (phase.kind !== 'form') return;
    const draft = phase.draft;
    phase = { kind: 'submitting', draft };
    try {
      // const result = await someIpcCall(draft);
      const result = 'ok';
      phase = { kind: 'success', result };
    } catch (err) {
      phase = { kind: 'error', message: String(err) };
    }
  }

  // 4. Derived state — computed from phase, never from separate flags.
  const canSubmit = $derived(
    phase.kind === 'form' && phase.draft.trim().length > 0
  );
</script>

<!-- 5. Phase-gated rendering. Each block is independent — no nested conditionals across phases. -->

{#if phase.kind === 'idle'}
  <button onclick={openForm}>Open Form</button>

{:else if phase.kind === 'loading'}
  <p>Loading...</p>

{:else if phase.kind === 'form'}
  <input bind:value={phase.draft} />
  <button onclick={submit} disabled={!canSubmit}>Submit</button>
  <button onclick={cancelForm}>Cancel</button>

{:else if phase.kind === 'submitting'}
  <!-- textarea/form not rendered here — committed, no going back -->
  <p>Submitting "{phase.draft}"...</p>

{:else if phase.kind === 'success'}
  <p>Done: {phase.result}</p>
  <button onclick={() => (phase = { kind: 'idle' })}>Close</button>

{:else if phase.kind === 'error'}
  <p>Error: {phase.message}</p>
  <button onclick={() => (phase = { kind: 'idle' })}>Try again</button>

{/if}

<!--
  ANTI-PATTERNS — do not do these:

  ❌ Multiple boolean flags for phase:
     let showForm = false; let isSubmitting = false; let showResults = false;
     → Allows impossible states (showForm && showResults simultaneously)

  ❌ Appending results below the form that submitted them:
     {#if showForm}...form...{/if}
     {#if results.length}...results...{/if}
     → Both can render simultaneously; form and results must be mutually exclusive

  ❌ Phase data scattered in top-level state:
     let draft = ''; let result = ''; // independent of phase
     → When phase transitions, stale data from prior phase is still present
-->
