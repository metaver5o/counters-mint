<script lang="ts">
  const NAME_RE = /^[A-Z]{4,12}$/

  let {
    filename,
    mime,
    preview,
    onselect,
  }: {
    filename: string
    mime: string
    preview: string
    onselect: (name: string) => void
  } = $props()

  let names = $state<string[]>([])
  let loading = $state(false)
  let err = $state<string | null>(null)

  async function suggest() {
    loading = true
    err = null
    names = []
    try {
      const r = await fetch('/ai/name-suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename, mime, preview }),
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      names = (data.names as string[]).filter((n) => NAME_RE.test(n)).slice(0, 3)
    } catch (e) {
      err = e instanceof Error ? e.message : 'Failed to get suggestions'
    } finally {
      loading = false
    }
  }
</script>

<div class="name-suggest">
  <button class="suggest-btn" onclick={suggest} disabled={loading}>
    {loading ? 'Thinking…' : 'Suggest names'}
  </button>
  {#if err}
    <p class="err">{err}</p>
  {/if}
  {#if names.length}
    <div class="chips">
      {#each names as name}
        <button class="chip" onclick={() => onselect(name)}>{name}</button>
      {/each}
    </div>
  {/if}
</div>

<style>
  .name-suggest { font-family: var(--mono) }
  .suggest-btn {
    background: var(--bg2); border: 1px solid var(--line); border-radius: 7px;
    color: var(--dim); font-family: inherit; font-size: 12px;
    padding: 7px 14px; cursor: pointer; transition: .15s; letter-spacing: .04em;
  }
  .suggest-btn:not(:disabled):hover { border-color: var(--copper); color: var(--ink) }
  .suggest-btn:disabled { opacity: .6; cursor: default }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px }
  .chip {
    background: var(--card); border: 1px solid var(--copper); border-radius: 6px;
    color: var(--copper); font-family: inherit; font-size: 13px;
    padding: 5px 14px; cursor: pointer; transition: .15s; letter-spacing: .06em;
  }
  .chip:hover { background: var(--copper); color: #1a0e08 }
  .err { font-size: 12px; color: #e74c3c; margin: 6px 0 0 }
</style>
