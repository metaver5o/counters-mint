<script lang="ts">
  type Tier = 'fastest' | 'standard' | 'economy'
  // Actual shape from GET /ai/fee-advice
  interface FeeAdvice {
    mempool: { fastest: number | '?'; hour: number | '?'; economy: number | '?' }
    recommendation: Tier
    reasoning: string
    estimated_cost_sats: number | null
  }

  let { selectedTier = $bindable<Tier>('economy') }: { selectedTier?: Tier } = $props()

  let advice = $state<FeeAdvice | null>(null)
  let loading = $state(false)
  let err = $state<string | null>(null)

  async function fetchAdvice() {
    loading = true
    err = null
    try {
      const r = await fetch('/ai/fee-advice')
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data: FeeAdvice = await r.json()
      advice = data
      // Set initial selection to AI recommendation
      if (!advice) selectedTier = data.recommendation
    } catch (e) {
      err = e instanceof Error ? e.message : 'Failed to load fee advice'
    } finally {
      loading = false
    }
  }

  $effect(() => {
    fetchAdvice()
    const id = setInterval(fetchAdvice, 60_000)
    return () => clearInterval(id)
  })

  // Map tier key → label + sat/vB from the mempool response
  const tierDefs: Array<{ key: Tier; label: string; getRate: (a: FeeAdvice) => number | '?' }> = [
    { key: 'fastest', label: 'Fastest', getRate: (a) => a.mempool.fastest },
    { key: 'standard', label: 'Standard', getRate: (a) => a.mempool.hour },
    { key: 'economy', label: 'Economy', getRate: (a) => a.mempool.economy },
  ]
</script>

<div class="fee-advisor">
  {#if loading && !advice}
    <p class="hint">Loading fee data…</p>
  {:else if err && !advice}
    <p class="hint err">{err}</p>
  {:else if advice}
    <div class="tiers">
      {#each tierDefs as { key, label, getRate }}
        {@const rate = getRate(advice)}
        {@const isRec = advice.recommendation === key}
        <button
          class="tier"
          class:selected={selectedTier === key}
          class:recommended={isRec}
          onclick={() => (selectedTier = key)}
        >
          {#if isRec}<span class="rec-badge">AI pick</span>{/if}
          <span class="tier-label">{label}</span>
          <span class="tier-rate">{rate} sat/vB</span>
          {#if isRec && advice.estimated_cost_sats}
            <span class="tier-cost">~{advice.estimated_cost_sats.toLocaleString()} sats</span>
          {/if}
        </button>
      {/each}
    </div>
    {#if advice.reasoning}
      <p class="reasoning">{advice.reasoning}</p>
    {/if}
  {/if}
</div>

<style>
  .fee-advisor { font-family: var(--mono) }
  .tiers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 10px }
  .tier {
    display: flex; flex-direction: column; gap: 4px; align-items: center;
    background: var(--bg2); border: 1px solid var(--line); border-radius: 9px;
    padding: 14px 10px; cursor: pointer; color: var(--ink);
    font-family: inherit; transition: .15s;
  }
  .tier:hover { border-color: var(--dim) }
  .tier.selected { border-color: var(--copper); box-shadow: 0 0 0 2px var(--copper-ghost) }
  .tier.recommended { border-color: var(--patina-dim) }
  .tier.recommended.selected { border-color: var(--copper); box-shadow: 0 0 0 2px var(--copper-ghost) }
  .rec-badge { font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--patina); background: var(--patina-dim); padding: 2px 6px; border-radius: 4px }
  .tier-label { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--dim) }
  .tier-rate { font-size: 15px; font-weight: 600; color: var(--ink) }
  .tier-cost { font-size: 11px; color: var(--faint) }
  .reasoning { font-size: 12px; color: var(--dim); margin: 0 }
  .hint { font-size: 12px; color: var(--faint); margin: 0 }
  .hint.err { color: #e74c3c }

  @media (max-width: 480px) {
    .tiers { grid-template-columns: 1fr }
  }
</style>
